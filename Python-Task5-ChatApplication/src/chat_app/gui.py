import re
from datetime import datetime

import gi  # type: ignore

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # type: ignore

from chat_app.client import ChatClient

EMOJI = {
    ":smile:": "😄",
    ":laugh:": "😂",
    ":heart:": "❤️",
    ":thumbsup:": "👍",
    ":wink:": "😉",
    ":sad:": "😢",
    ":fire:": "🔥",
    ":wave:": "👋",
    ":thinking:": "🤔",
    ":check:": "✅",
}


def convert_emoji(text):
    pattern = re.compile(r":[a-z]+:")
    return pattern.sub(lambda match: EMOJI.get(match.group(), match.group()), text)


class ChatApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.yash.OIBSIPChat")
        self.client = None
        self.window = None
        self.current_username = ""
        self.current_room = "general"
        self.current_room_name = "General"
        self.current_room_is_public = True
        self.pending_private_invite = None
        self.invite_slot = None
        self.room_names = {"GENERAL": "General", "general": "General"}
        self.room_member_counts = {}
        self.lobby_metric_values = {}
        self.chat_empty_state = None
        self.chat_presence_label = None
        self.rooms_container = None
        self.room_list_status = None
        self.messages_box = None
        self.chat_scroll = None
        self.message_entry = None
        self.room_entry = None
        self.room_label = None
        self.status = None
        self.auth_buttons = []
        self.auth_fields = {}
        self.auth_action = "login"
        self.window_active = False
        self.css_provider = None

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("Relay")
        self.window.set_default_size(1000, 700)
        self.window.set_size_request(360, 420)
        self.window.connect(
            "notify::is-active",
            self.on_window_active_changed,
        )

        self.install_styles()
        self.show_login()
        self.window.present()

    def on_window_active_changed(self, window, _param):
        self.window_active = window.is_active()

    def install_styles(self):
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(b"""
            .brand-title {
                font-size: 30px;
                font-weight: 800;
                color: @accent_color;
            }
            .auth-card {
                background-color: alpha(@card_bg_color, 0.97);
                border-radius: 24px;
                padding: 24px;
                box-shadow: 0 12px 30px rgba(0,0,0,0.22);
            }
            .auth-brand-panel {
                padding: 16px;
                border-radius: 17px;
                background-color: alpha(@accent_bg_color, 0.14);
            }
            .auth-brand-mark {
                min-width: 50px;
                min-height: 50px;
                border-radius: 15px;
                background-color: alpha(@accent_bg_color, 0.22);
                font-size: 25px;
            }
            .auth-brand-caption {
                font-size: 12px;
            }
            .auth-tabs {
                padding: 4px;
                border-radius: 12px;
                background-color: alpha(@window_fg_color, 0.07);
            }
            button.auth-tab {
                min-height: 36px;
                border-radius: 9px;
                background: transparent;
                box-shadow: none;
            }
            button.auth-tab:checked {
                color: @accent_fg_color;
                background-color: @accent_bg_color;
                box-shadow: 0 1px 3px rgba(0,0,0,0.22);
            }
            .lobby-hero {
                padding: 22px;
                border-radius: 20px;
                background-color: alpha(@accent_bg_color, 0.18);
            }
            .lobby-stat {
                padding: 16px 18px;
                border-radius: 16px;
                background-color: alpha(@card_bg_color, 0.72);
            }
            .invite-card {
                padding: 16px;
                border-radius: 16px;
                background-color: alpha(@accent_bg_color, 0.14);
            }
            .private-access-card {
                padding: 18px;
                border-radius: 16px;
                background-color: alpha(@card_bg_color, 0.72);
            }
            .private-room-icon {
                min-width: 42px;
                min-height: 42px;
                border-radius: 13px;
                background-color: alpha(@window_fg_color, 0.08);
                font-size: 19px;
            }
            .room-row {
                padding: 16px;
                border-radius: 16px;
                background-color: alpha(@card_bg_color, 0.82);
            }
            .room-icon {
                min-width: 48px;
                min-height: 48px;
                border-radius: 14px;
                background-color: alpha(@accent_bg_color, 0.2);
                font-size: 22px;
            }
            .member-count {
                padding: 6px 10px;
                border-radius: 999px;
                background-color: alpha(@window_fg_color, 0.08);
            }
            .online-dot {
                color: #62d69a;
                font-size: 12px;
            }
            .chat-empty-state {
                padding: 28px;
                border-radius: 20px;
                background-color: alpha(@card_bg_color, 0.55);
            }
            .chat-bubble {
                padding: 10px 14px;
                border-radius: 16px;
            }
            .message-own {
                background-color: alpha(@accent_bg_color, 0.22);
            }
            .message-other {
                background-color: alpha(@card_bg_color, 0.9);
            }
            .chat-composer {
                padding: 10px;
                border-radius: 18px;
                background-color: alpha(@card_bg_color, 0.8);
            }
        """)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                self.css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def make_theme_selector(self):
        selector = Gtk.DropDown.new_from_strings(["System", "Light", "Dark"])
        selector.set_tooltip_text("Choose appearance")
        manager = Adw.StyleManager.get_default()
        scheme = manager.get_color_scheme()

        if scheme == Adw.ColorScheme.FORCE_LIGHT:
            selector.set_selected(1)
        elif scheme == Adw.ColorScheme.FORCE_DARK:
            selector.set_selected(2)
        else:
            selector.set_selected(0)

        selector.connect("notify::selected", self.on_theme_changed)
        return selector

    def on_theme_changed(self, selector, _param):
        schemes = [
            Adw.ColorScheme.DEFAULT,
            Adw.ColorScheme.FORCE_LIGHT,
            Adw.ColorScheme.FORCE_DARK,
        ]
        selected = selector.get_selected()
        if selected < len(schemes):
            Adw.StyleManager.get_default().set_color_scheme(schemes[selected])

    def make_header(self, title, subtitle=None):
        header = Adw.HeaderBar()
        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
        )
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("heading")
        title_box.append(title_label)

        if subtitle:
            subtitle_label = Gtk.Label(label=subtitle)
            subtitle_label.add_css_class("dim-label")
            subtitle_label.add_css_class("caption")
            title_box.append(subtitle_label)

        header.set_title_widget(title_box)
        header.pack_end(self.make_theme_selector())
        return header

    def make_password_row(self, title):
        row = Adw.PasswordEntryRow()
        row.set_title(title)
        container = Gtk.ListBox()
        container.set_selection_mode(Gtk.SelectionMode.NONE)
        container.add_css_class("boxed-list")
        container.append(row)
        return row, container

    def make_username_field(self):
        entry = Gtk.Entry()
        entry.set_placeholder_text("Username")
        entry.set_hexpand(True)
        entry.set_activates_default(True)
        container = Gtk.ListBox()
        container.set_selection_mode(Gtk.SelectionMode.NONE)
        container.add_css_class("boxed-list")
        container.append(entry)
        return entry, container

    def make_status_label(self):
        label = Gtk.Label()
        label.set_wrap(True)
        label.add_css_class("dim-label")
        return label

    def make_button(self, text, callback, primary=False):
        button = Gtk.Button(label=text)
        button.set_hexpand(True)
        button.connect("clicked", callback)
        button.add_css_class("pill")
        if primary:
            button.add_css_class("suggested-action")
        return button

    def set_auth_busy(self, busy):
        for button in self.auth_buttons:
            button.set_sensitive(not busy)
        for field in self.auth_fields.values():
            field.set_sensitive(not busy)

    def show_login(self):
        self.messages_box = None
        self.message_entry = None
        self.room_entry = None
        self.rooms_container = None
        self.room_list_status = None
        self.auth_action = "login"
        self.auth_buttons = []
        self.auth_fields = {}

        page = Adw.ToolbarView()
        page.add_top_bar(self.make_header("Relay"))

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scroll.set_vexpand(True)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(440)

        outer_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        outer_box.set_margin_top(24)
        outer_box.set_margin_bottom(24)
        outer_box.set_margin_start(24)
        outer_box.set_margin_end(24)

        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        card.add_css_class("auth-card")
        card.set_margin_top(12)
        card.set_margin_bottom(12)
        card.set_margin_start(12)
        card.set_margin_end(12)

        brand_panel = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=14,
        )
        brand_panel.add_css_class("auth-brand-panel")
        brand_mark = Gtk.Label(label="💬")
        brand_mark.add_css_class("auth-brand-mark")
        brand_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        brand = Gtk.Label(label="Relay", xalign=0)
        brand.add_css_class("brand-title")
        brand_caption = Gtk.Label(label="Chat with your community", xalign=0)
        brand_caption.add_css_class("dim-label")
        brand_caption.add_css_class("auth-brand-caption")
        brand_caption.set_wrap(True)
        brand_text.append(brand)
        brand_text.append(brand_caption)
        brand_panel.append(brand_mark)
        brand_panel.append(brand_text)

        intro = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        intro_title = Gtk.Label(label="Welcome back", xalign=0.5)
        intro_title.add_css_class("title-2")
        intro_description = Gtk.Label(
            label="Sign in to continue.",
            xalign=0.5,
        )
        intro_description.add_css_class("dim-label")
        intro_description.set_justify(Gtk.Justification.CENTER)
        intro.append(intro_title)
        intro.append(intro_description)

        self.auth_heading = intro_title
        self.auth_description = intro_description
        self.auth_form_slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.status = self.make_status_label()
        self.status.set_justify(Gtk.Justification.CENTER)

        login_button = self.make_button("Sign In", self.on_login, primary=True)
        register_button = self.make_button("Create Account", self.on_register, primary=True)
        self.auth_buttons = [login_button, register_button]

        tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tab_bar.add_css_class("auth-tabs")
        tab_bar.set_homogeneous(True)
        sign_in_tab = Gtk.ToggleButton(label="Sign In")
        create_account_tab = Gtk.ToggleButton(label="Create Account")
        sign_in_tab.add_css_class("auth-tab")
        create_account_tab.add_css_class("auth-tab")
        create_account_tab.set_group(sign_in_tab)
        sign_in_tab.set_hexpand(True)
        create_account_tab.set_hexpand(True)
        sign_in_tab.set_active(True)
        sign_in_tab.connect(
            "toggled",
            lambda button: self.select_auth_page("signin")
            if button.get_active() else None,
        )
        create_account_tab.connect(
            "toggled",
            lambda button: self.select_auth_page("create-account")
            if button.get_active() else None,
        )
        tab_bar.append(sign_in_tab)
        tab_bar.append(create_account_tab)

        self.username, username_list = self.make_username_field()
        self.password, password_list = self.make_password_row("Password")
        self.auth_fields["login_username"] = self.username
        self.auth_fields["login_password"] = self.password
        sign_in_form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sign_in_form.append(username_list)
        sign_in_form.append(password_list)
        sign_in_form.append(login_button)
        self.auth_pages = {"signin": sign_in_form}

        self.register_username, register_username_list = self.make_username_field()
        self.register_password, register_password_list = self.make_password_row("Password")
        self.confirm_password, confirm_password_list = self.make_password_row("Confirm password")
        self.auth_fields["register_username"] = self.register_username
        self.auth_fields["register_password"] = self.register_password
        self.auth_fields["confirm_password"] = self.confirm_password
        register_form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        register_form.append(register_username_list)
        register_form.append(register_password_list)
        register_form.append(confirm_password_list)
        register_form.append(register_button)
        self.auth_pages["create-account"] = register_form
        self.auth_form_slot.append(sign_in_form)

        card.append(brand_panel)
        card.append(intro)
        card.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        card.append(tab_bar)
        card.append(self.auth_form_slot)
        card.append(self.status)

        outer_box.append(card)
        clamp.set_child(outer_box)
        scroll.set_child(clamp)
        page.set_content(scroll)
        self.window.set_content(page)

    def select_auth_page(self, page_name):
        current = self.auth_form_slot.get_first_child()
        if current is not None:
            self.auth_form_slot.remove(current)
        self.auth_form_slot.append(self.auth_pages[page_name])

        if page_name == "signin":
            self.auth_heading.set_text("Welcome back")
            self.auth_description.set_text("Sign in to continue.")
        else:
            self.auth_heading.set_text("Create your account")
            self.auth_description.set_text("Join Relay to start chatting.")

    def ensure_connected(self):
        if self.client and self.client.running:
            return True

        try:
            self.client = ChatClient(on_message=self.receive_message)
            self.client.connect()
            return True
        except (OSError, ConnectionError, TimeoutError) as exc:
            self.status.set_text(f"Cannot connect to server: {exc}")
            self.client = None
            return False

    def on_login(self, *_):
        if not self.ensure_connected():
            return
        self.auth_action = "login"
        self.set_auth_busy(True)
        try:
            self.client.login(
                self.username.get_text().strip(),
                self.password.get_text(),
            )
        except (OSError, ConnectionError, ValueError) as exc:
            self.status.set_text(str(exc))
            self.set_auth_busy(False)

    def on_register(self, *_):
        if self.register_password.get_text() != self.confirm_password.get_text():
            self.status.set_text("Passwords do not match.")
            return
        if not self.ensure_connected():
            return
        self.auth_action = "register"
        self.set_auth_busy(True)
        try:
            self.client.register(
                self.register_username.get_text().strip(),
                self.register_password.get_text(),
            )
        except (OSError, ConnectionError, ValueError) as exc:
            self.status.set_text(str(exc))
            self.set_auth_busy(False)

    def sign_out(self, *_):
        client = self.client
        self.client = None
        if client:
            client.disconnect()
        self.current_username = ""
        self.current_room = "general"
        self.chat_presence_label = None
        self.show_login()

    def make_account_menu(self):
        button = Gtk.MenuButton()
        button.set_tooltip_text("Account options")
        button_avatar = Adw.Avatar.new(32, self.current_username, True)
        button.set_child(button_avatar)

        popover = Gtk.Popover()
        menu = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )
        menu.set_margin_top(12)
        menu.set_margin_bottom(12)
        menu.set_margin_start(12)
        menu.set_margin_end(12)

        profile = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        profile_avatar = Adw.Avatar.new(48, self.current_username, True)
        profile_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        profile_name = Gtk.Label(label=self.current_username, xalign=0)
        profile_name.add_css_class("heading")
        profile_caption = Gtk.Label(label="Relay account", xalign=0)
        profile_caption.add_css_class("dim-label")
        profile_caption.add_css_class("caption")
        profile_text.append(profile_name)
        profile_text.append(profile_caption)
        profile.append(profile_avatar)
        profile.append(profile_text)
        menu.append(profile)
        menu.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        if self.rooms_container is None:
            browse_rooms_btn = Gtk.Button(label="Browse Public Rooms")
            browse_rooms_btn.connect("clicked", self.on_browse_rooms)

            join_room_menu_btn = Gtk.Button(label="Join with Invite Code")
            join_room_menu_btn.connect("clicked", self.on_join_room_dialog)

            create_room_menu_btn = Gtk.Button(label="Create a Room")
            create_room_menu_btn.connect("clicked", self.on_create_room_dialog)

            menu.append(browse_rooms_btn)
            menu.append(join_room_menu_btn)
            menu.append(create_room_menu_btn)
            menu.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        logout = Gtk.Button(label="Sign out")
        logout.add_css_class("destructive-action")
        logout.connect("clicked", self.sign_out)
        menu.append(logout)

        popover.set_child(menu)
        button.set_popover(popover)
        return button

    def show_room_lobby(self, username):
        self.current_username = username
        self.messages_box = None
        self.message_entry = None
        self.chat_scroll = None
        self.chat_presence_label = None
        self.chat_empty_state = None
        self.lobby_metric_values = {}
        self.rooms_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )
        self.room_list_status = Gtk.Label(label="Loading public rooms…")
        self.room_list_status.set_wrap(True)
        self.room_list_status.add_css_class("dim-label")

        page = Adw.ToolbarView()
        header = self.make_header("Public Rooms", f"Choose a room · Signed in as {username}")
        header.pack_end(self.make_account_menu())
        page.add_top_bar(header)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(840)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        layout.set_margin_top(28)
        layout.set_margin_bottom(24)
        layout.set_margin_start(28)
        layout.set_margin_end(28)

        hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        hero.add_css_class("lobby-hero")
        hero.set_valign(Gtk.Align.CENTER)
        hero_icon = Gtk.Label(label="🌐")
        hero_icon.add_css_class("title-1")
        hero_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        hero_text.set_hexpand(True)
        intro_title = Gtk.Label(label=f"Welcome, {username}", xalign=0)
        intro_title.add_css_class("title-2")
        intro_subtitle = Gtk.Label(
            label="Discover a public room, meet the community, and jump into the conversation."
        )
        intro_subtitle.add_css_class("dim-label")
        intro_subtitle.set_wrap(True)
        intro_subtitle.set_xalign(0)
        hero_text.append(intro_title)
        hero_text.append(intro_subtitle)
        hero.append(hero_icon)
        hero.append(hero_text)

        stats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        room_stat, self.lobby_metric_values["rooms"] = self.make_lobby_metric("0", "Public rooms")
        people_stat, self.lobby_metric_values["people"] = self.make_lobby_metric(
            "0", "People in public rooms"
        )
        access_stat, _ = self.make_lobby_metric("Open", "Anyone can join")
        stats_row.append(room_stat)
        stats_row.append(people_stat)
        stats_row.append(access_stat)

        public_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        public_title = Gtk.Label(label="Public rooms", xalign=0)
        public_title.add_css_class("title-3")
        public_hint = Gtk.Label(
            label="Discoverable by everyone and open to join.", xalign=0
        )
        public_hint.add_css_class("dim-label")
        public_header.append(public_title)
        public_header.append(public_hint)

        room_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        room_toolbar.set_halign(Gtk.Align.END)
        refresh_button = Gtk.Button(label="Refresh")
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.connect("clicked", self.on_refresh_rooms)
        create_button = Gtk.Button(label="Create a room")
        create_button.add_css_class("suggested-action")
        create_button.connect("clicked", self.on_create_room_dialog)
        room_toolbar.append(refresh_button)
        room_toolbar.append(create_button)

        private_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        private_access = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=14
        )
        private_access.add_css_class("private-access-card")
        private_icon = Gtk.Label(label="🔒")
        private_icon.add_css_class("private-room-icon")
        private_details = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        private_details.set_hexpand(True)
        private_title = Gtk.Label(label="Private rooms", xalign=0)
        private_title.add_css_class("heading")
        private_hint = Gtk.Label(
            label="Invite-only and hidden from the public directory. Enter a code shared by the room creator.",
            xalign=0,
        )
        private_hint.add_css_class("dim-label")
        private_hint.set_wrap(True)
        private_details.append(private_title)
        private_details.append(private_hint)
        private_join = Gtk.Button(label="Enter invite code")
        private_join.connect("clicked", self.on_join_room_dialog)
        private_access.append(private_icon)
        private_access.append(private_details)
        private_access.append(private_join)
        self.invite_slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        private_section.append(private_access)
        private_section.append(self.invite_slot)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(False)
        scroller.set_min_content_height(72)
        scroller.set_max_content_height(320)
        scroller.set_propagate_natural_height(True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.rooms_container)

        layout.append(hero)
        layout.append(stats_row)
        layout.append(public_header)
        layout.append(room_toolbar)
        layout.append(scroller)
        layout.append(private_section)
        layout.append(self.room_list_status)
        clamp.set_child(layout)
        page.set_content(clamp)
        self.window.set_content(page)
        self.window.set_default_widget(refresh_button)
        self.window.present()
        if self.pending_private_invite:
            self.render_private_invite(*self.pending_private_invite)
        if self.client and self.client.running:
            self.client.list_rooms()

    def make_lobby_metric(self, value, caption):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("lobby-stat")
        card.set_hexpand(True)
        value_label = Gtk.Label(label=value, xalign=0)
        value_label.add_css_class("title-2")
        caption_label = Gtk.Label(label=caption, xalign=0)
        caption_label.add_css_class("dim-label")
        caption_label.add_css_class("caption")
        card.append(value_label)
        card.append(caption_label)
        return card, value_label

    def render_room_directory(self, rooms):
        self.room_names = {room["id"]: room["name"] for room in rooms}
        self.room_member_counts = {
            room["id"]: int(room.get("member_count", 0)) for room in rooms
        }
        total_people = sum(self.room_member_counts.values())
        if self.lobby_metric_values:
            self.lobby_metric_values["rooms"].set_text(str(len(rooms)))
            self.lobby_metric_values["people"].set_text(str(total_people))
        if self.chat_presence_label:
            if self.current_room_is_public:
                room_count = self.room_member_counts.get(self.current_room, 0)
                presence = f"Connected as {self.current_username} · {room_count} online"
            else:
                presence = f"Private room · Connected as {self.current_username}"
            self.chat_presence_label.set_text(presence)

        if self.rooms_container is None:
            return
        while child := self.rooms_container.get_first_child():
            self.rooms_container.remove(child)

        for room in rooms:
            room_id_value = room["id"]
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            row.add_css_class("room-row")
            row.set_valign(Gtk.Align.CENTER)

            icon = Gtk.Label(label="💬")
            icon.add_css_class("room-icon")

            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            details.set_hexpand(True)
            title = Gtk.Label(label=room["name"], xalign=0)
            title.add_css_class("heading")
            if room_id_value.upper() == "GENERAL":
                description = "Public · The community lounge — say hello to everyone."
            else:
                description = f"Public · Created by {room['created_by']}"
            subtitle = Gtk.Label(label=description, xalign=0)
            subtitle.add_css_class("dim-label")
            subtitle.add_css_class("caption")
            details.append(title)
            details.append(subtitle)

            count = self.room_member_counts[room_id_value]
            people = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            people.add_css_class("member-count")
            dot = Gtk.Label(label="●")
            dot.add_css_class("online-dot" if count else "dim-label")
            count_label = Gtk.Label(
                label=f"{count} online" if count != 1 else "1 online"
            )
            count_label.add_css_class("dim-label")
            people.append(dot)
            people.append(count_label)

            join_button = Gtk.Button(label="Join room")
            join_button.add_css_class("suggested-action")
            join_button.connect(
                "clicked",
                lambda _button, room_id=room_id_value: self.join_public_room(room_id),
            )
            row.append(icon)
            row.append(details)
            row.append(people)
            row.append(join_button)
            if (
                room_id_value.upper() != "GENERAL"
                and room["created_by"].casefold() == self.current_username.casefold()
            ):
                delete_button = Gtk.Button()
                delete_button.set_icon_name("user-trash-symbolic")
                delete_button.set_tooltip_text("Delete this room")
                delete_button.add_css_class("destructive-action")
                delete_button.connect(
                    "clicked",
                    lambda _button, room_id=room_id_value, name=room["name"]:
                        self.confirm_delete_public_room(room_id, name),
                )
                row.append(delete_button)
            self.rooms_container.append(row)

        if not rooms:
            empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty.set_halign(Gtk.Align.CENTER)
            empty.set_valign(Gtk.Align.CENTER)
            empty_title = Gtk.Label(label="Your community starts here")
            empty_title.add_css_class("title-3")
            empty_hint = Gtk.Label(
                label="Create a public room and invite everyone to join the conversation."
            )
            empty_hint.add_css_class("dim-label")
            empty_hint.set_wrap(True)
            empty.append(empty_title)
            empty.append(empty_hint)
            self.rooms_container.append(empty)

    def render_private_invite(self, room_name, invite_code):
        if not self.invite_slot or not invite_code:
            return
        while child := self.invite_slot.get_first_child():
            self.invite_slot.remove(child)

        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.add_css_class("invite-card")
        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        details.set_hexpand(True)
        title = Gtk.Label(label=f"{room_name} is private", xalign=0)
        title.add_css_class("heading")
        description = Gtk.Label(
            label=f"Share invite code {invite_code} with people you want to join.",
            xalign=0,
        )
        description.add_css_class("dim-label")
        details.append(title)
        details.append(description)

        copy_button = Gtk.Button(label="Copy code")
        copy_button.connect(
            "clicked", lambda _button: self.copy_invite_code(invite_code)
        )
        join_button = Gtk.Button(label="Join room")
        join_button.add_css_class("suggested-action")
        join_button.connect(
            "clicked", lambda _button: self.join_private_room(invite_code)
        )
        card.append(details)
        card.append(copy_button)
        card.append(join_button)
        self.invite_slot.append(card)

    def copy_invite_code(self, invite_code):
        display = Gdk.Display.get_default()
        if display:
            display.get_clipboard().set(invite_code)
            if self.room_list_status:
                self.room_list_status.set_text("Invite code copied to clipboard.")

    def join_private_room(self, invite_code):
        if self.client and self.client.running:
            self.client.join_room(invite_code)
            if self.room_list_status:
                self.room_list_status.set_text("Joining private room…")

    def confirm_delete_public_room(self, room_id, room_name):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Delete {room_name}?\nThis permanently removes the room and its message history. Everyone in it will return to the room directory.",
        )
        dialog.connect(
            "response",
            lambda dlg, response: self.delete_public_room(room_id)
            if response == Gtk.ResponseType.OK else None,
        )
        dialog.connect("response", lambda dlg, _response: dlg.destroy())
        dialog.present()

    def delete_public_room(self, room_id):
        if self.client and self.client.running:
            self.client.delete_room(room_id)
            if self.room_list_status:
                self.room_list_status.set_text("Deleting room…")

    def join_public_room(self, room_id):
        if self.client and self.client.running:
            self.client.join_room(room_id)
            if self.room_list_status:
                self.room_list_status.set_text("Joining room…")

    def on_refresh_rooms(self, *_):
        if self.client and self.client.running:
            self.client.list_rooms()

    def on_browse_rooms(self, *_):
        self.show_room_lobby(self.current_username)

    def show_chat(self, username):
        self.current_username = username
        self.rooms_container = None
        self.room_list_status = None
        room_name = self.current_room_name
        room_count = self.room_member_counts.get(self.current_room, 1)
        if self.current_room_is_public:
            presence = f"Connected as {username} · {room_count} online"
        else:
            presence = f"Private room · Connected as {username}"

        page = Adw.ToolbarView()
        header = self.make_header(room_name, presence)
        title_widget = header.get_title_widget()
        self.chat_presence_label = title_widget.get_last_child() if title_widget else None
        header.pack_end(self.make_account_menu())
        page.add_top_bar(header)

        layout = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )
        layout.set_margin_top(12)
        layout.set_margin_bottom(12)
        layout.set_margin_start(16)
        layout.set_margin_end(16)

        self.chat_scroll = Gtk.ScrolledWindow()
        self.chat_scroll.set_vexpand(True)
        self.chat_scroll.set_hexpand(True)
        self.chat_scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )

        self.messages_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )
        self.messages_box.set_margin_top(12)
        self.messages_box.set_margin_bottom(12)
        self.messages_box.set_margin_start(4)
        self.messages_box.set_margin_end(4)
        self.chat_empty_state = self.make_chat_empty_state(room_name)
        self.messages_box.append(self.chat_empty_state)
        self.chat_scroll.set_child(self.messages_box)

        composer = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        composer.add_css_class("chat-composer")

        self.message_entry = Gtk.Entry()
        self.message_entry.set_placeholder_text(f"Message {room_name}…")
        self.message_entry.set_hexpand(True)
        self.message_entry.set_activates_default(True)
        self.message_entry.connect("activate", self.on_send)

        send_button = Gtk.Button()
        send_button.set_icon_name("mail-send-symbolic")
        send_button.set_tooltip_text("Send message")
        send_button.add_css_class("suggested-action")
        send_button.add_css_class("circular")
        send_button.connect("clicked", self.on_send)

        composer.append(self.message_entry)
        composer.append(send_button)

        layout.append(self.chat_scroll)
        layout.append(composer)
        page.set_content(layout)
        self.window.set_content(page)
        self.window.set_default_widget(send_button)
        self.window.present()

    def make_chat_empty_state(self, room_name):
        state = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        state.add_css_class("chat-empty-state")
        state.set_halign(Gtk.Align.CENTER)
        state.set_valign(Gtk.Align.CENTER)
        state.set_vexpand(True)

        icon = Gtk.Label(label="💬")
        icon.add_css_class("title-1")
        title = Gtk.Label(label=f"Welcome to {room_name}")
        title.add_css_class("title-2")
        description = Gtk.Label(
            label="There are no messages here yet. Start the conversation with a friendly hello."
        )
        description.add_css_class("dim-label")
        description.set_wrap(True)
        description.set_justify(Gtk.Justification.CENTER)
        description.set_max_width_chars(52)
        privacy_text = (
            "Messages in this public room are visible to everyone."
            if self.current_room_is_public
            else "This room is private. Share its invite code only with people you trust."
        )
        privacy = Gtk.Label(label=privacy_text)
        privacy.add_css_class("caption")
        privacy.add_css_class("dim-label")

        state.append(icon)
        state.append(title)
        state.append(description)
        state.append(privacy)
        return state

    def clear_chat_empty_state(self):
        if self.chat_empty_state and self.messages_box:
            self.messages_box.remove(self.chat_empty_state)
        self.chat_empty_state = None

    def on_join_room_dialog(self, *_):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Join a private room\nEnter the invite code shared by its creator:",
        )

        entry = Gtk.Entry()
        entry.set_placeholder_text("Private room invite code")
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        entry.set_margin_top(6)
        entry.set_margin_bottom(6)
        dialog.get_content_area().append(entry)

        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.OK:
                invite_code = entry.get_text().strip()
                if invite_code and self.client and self.client.running:
                    try:
                        self.client.join_room(invite_code)
                        if self.room_list_status:
                            self.room_list_status.set_text("Checking invite code…")
                    except (OSError, ConnectionError, ValueError) as exc:
                        if self.room_list_status:
                            self.room_list_status.set_text(str(exc))
                        else:
                            self.add_system_message(str(exc))
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def on_create_room_dialog(self, *_):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Create a New Chat Room\nEnter a name for the new chat room:",
        )

        entry = Gtk.Entry()
        entry.set_placeholder_text("Room name (e.g. developers)")
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        entry.set_margin_top(6)
        entry.set_margin_bottom(6)

        content_area = dialog.get_content_area()
        content_area.append(entry)
        access_label = Gtk.Label(label="Who can join?", xalign=0)
        access_label.set_margin_start(12)
        access_label.set_margin_top(8)
        access = Gtk.DropDown.new_from_strings([
            "Public · anyone can find and join",
            "Private · invite code required",
        ])
        access.set_margin_start(12)
        access.set_margin_end(12)
        access.set_margin_bottom(8)
        content_area.append(access_label)
        content_area.append(access)

        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.OK:
                room_name = entry.get_text().strip()
                if room_name and self.client and self.client.running:
                    try:
                        self.client.create_room(
                            room_name, is_public=(access.get_selected() == 0)
                        )
                    except (OSError, ConnectionError, ValueError) as exc:
                        self.add_system_message(str(exc))
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def receive_message(self, message):
        GLib.idle_add(self.handle_message, message)

    def handle_message(self, message):
        kind = message.get("type")

        if kind == "auth":
            if not message.get("success"):
                if self.status:
                    self.status.set_text(message.get("text", "Authentication failed."))
                self.set_auth_busy(False)
                return GLib.SOURCE_REMOVE

            if self.auth_action == "register":
                if self.status:
                    self.status.set_text(
                        "Account created. Sign in with your new credentials."
                    )
                if self.client:
                    self.client.disconnect()
                    self.client = None
                self.set_auth_busy(False)
                return GLib.SOURCE_REMOVE

            self.current_username = message.get(
                "username", self.username.get_text().strip()
            )
            self.current_room = message.get("room", "GENERAL")
            self.current_room_name = "General"
            self.set_auth_busy(False)
            self.show_room_lobby(self.current_username)
            return GLib.SOURCE_REMOVE

        if kind == "room_list":
            self.render_room_directory(message.get("rooms", []))
            if self.room_list_status:
                room_total = len(message.get("rooms", []))
                room_word = "room" if room_total == 1 else "rooms"
                self.room_list_status.set_text(
                    f"{room_total} public {room_word} · online counts update live."
                )
            return GLib.SOURCE_REMOVE

        if kind == "room_deleted":
            if message.get("room") == self.current_room and self.message_entry:
                self.current_room = "GENERAL"
                self.current_room_name = "General"
                self.current_room_is_public = True
                self.show_room_lobby(self.current_username)
            if self.room_list_status:
                self.room_list_status.set_text(message.get("text", "Room deleted."))
            return GLib.SOURCE_REMOVE

        if kind == "room_created":
            if self.rooms_container is None:
                self.show_room_lobby(self.current_username)
            if message.get("is_public", True):
                if self.room_list_status:
                    self.room_list_status.set_text(message.get("text", "Public room created."))
            else:
                self.pending_private_invite = (
                    message.get("room_name", "Private room"),
                    message.get("room", ""),
                )
                self.render_private_invite(*self.pending_private_invite)
            return GLib.SOURCE_REMOVE

        if kind == "room_joined":
            self.current_room = message.get("room", "GENERAL")
            self.current_room_name = message.get(
                "room_name", self.room_names.get(self.current_room, self.current_room)
            )
            self.current_room_is_public = message.get("is_public", True)
            self.show_chat(self.current_username)
            return GLib.SOURCE_REMOVE

        if kind == "history":
            if self.messages_box:
                while child := self.messages_box.get_first_child():
                    self.messages_box.remove(child)
            self.chat_empty_state = None
            messages = message.get("messages", [])
            for item in messages:
                self.add_message(
                    item.get("username", "?"),
                    item.get("content", ""),
                    item.get("created_at", ""),
                )
            if not messages and self.messages_box:
                self.chat_empty_state = self.make_chat_empty_state(
                    self.current_room_name
                )
                self.messages_box.append(self.chat_empty_state)
            return GLib.SOURCE_REMOVE

        if kind == "chat":
            sender = message.get("username", "?")
            text = message.get("text", "")
            room = message.get("room", self.current_room)

            if room == self.current_room:
                self.add_message(sender, text, message.get("time", ""))

            if sender != self.current_username and not self.window_active:
                notification = Gio.Notification.new(f"Message from {sender}")
                notification.set_body(text)
                self.send_notification(notification)

        elif kind == "system":
            self.add_system_message(message.get("text", ""))

        elif kind == "error":
            if self.room_list_status:
                self.room_list_status.set_text(message.get("text", "An error occurred."))
            else:
                self.add_system_message(message.get("text", "An error occurred."))

        return GLib.SOURCE_REMOVE

    def send_notification(self, notification):
        self.send_notification_impl(notification)

    def send_notification_impl(self, notification):
        self.send_notification_to_app(notification)

    def send_notification_to_app(self, notification):
        self.send_notification(notification)

    def add_message(self, username, text, timestamp=""):
        if self.messages_box is None:
            return

        self.clear_chat_empty_state()
        display_time = self.format_timestamp(timestamp)
        is_own = username == self.current_username

        row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        row.set_hexpand(True)
        row.set_halign(Gtk.Align.END if is_own else Gtk.Align.START)

        bubble = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=5,
        )
        bubble.add_css_class("chat-bubble")
        bubble.add_css_class("message-own" if is_own else "message-other")

        heading_text = display_time if is_own else f"{username}  ·  {display_time}"
        heading = Gtk.Label(label=heading_text, xalign=0)
        heading.add_css_class("dim-label")
        heading.add_css_class("caption")

        body = Gtk.Label(label=text, xalign=0)
        body.set_wrap(True)
        body.set_selectable(True)
        body.set_max_width_chars(55)

        bubble.append(heading)
        bubble.append(body)
        row.append(bubble)
        self.messages_box.append(row)
        GLib.idle_add(self.scroll_to_latest)

    @staticmethod
    def format_timestamp(timestamp):
        if not timestamp:
            return ""
        try:
            parsed = datetime.fromisoformat(timestamp)
            return parsed.astimezone().strftime("%I:%M %p").lstrip("0")
        except ValueError, TypeError:
            return timestamp

    def add_system_message(self, text):
        if self.messages_box is None:
            return

        label = Gtk.Label(label=text)
        label.add_css_class("dim-label")
        label.add_css_class("caption")
        label.set_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        if self.chat_empty_state:
            self.messages_box.prepend(label)
        else:
            self.messages_box.append(label)
        GLib.idle_add(self.scroll_to_latest)

    def scroll_to_latest(self):
        if self.chat_scroll is None:
            return GLib.SOURCE_REMOVE

        adjustment = self.chat_scroll.get_vadjustment()
        adjustment.set_value(
            max(
                adjustment.get_lower(),
                adjustment.get_upper() - adjustment.get_page_size(),
            )
        )
        return GLib.SOURCE_REMOVE

    def on_send(self, *_):
        if not self.client or not self.client.running:
            self.add_system_message("Not connected to the server.")
            return

        text = convert_emoji(self.message_entry.get_text().strip())
        if not text:
            return

        try:
            self.client.send_message(text)
            self.message_entry.set_text("")
        except (OSError, ConnectionError, ValueError) as exc:
            self.add_system_message(f"Send failed: {exc}")


def main():
    app = ChatApplication()
    app.run()


if __name__ == "__main__":
    main()
