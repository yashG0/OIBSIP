from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk

from chat_app.client import ChatClient


class ChatApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.yash.OIBSIPChat")

        self.client = None
        self.auth_action = None
        self.window = None
        self.messages_box = None
        self.chat_scroll = None
        self.message_entry = None
        self.current_username = ""
        self.auth_buttons = []
        self.status = None
        self.register_status = None
        self.css_provider = None

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("OIBSIP Chat")
        self.window.set_default_size(1000, 700)
        self.window.set_size_request(360, 420)

        self.install_styles()
        self.show_login()
        self.window.present()

    # ---------------------------------------------------------
    # Theme and styling
    # ---------------------------------------------------------

    def install_styles(self):
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(b"""
            .brand-title {
                font-size: 28px;
                font-weight: 800;
                letter-spacing: -0.8px;
            }

            .auth-card {
                padding: 28px;
                border-radius: 20px;
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

            .section-caption {
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            .status-dot {
                color: #2ec27e;
            }
        """)

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def make_theme_selector(self):
        selector = Gtk.DropDown.new_from_strings(["System", "Light", "Dark"])
        selector.set_tooltip_text("Choose appearance")
        selector.set_size_request(110, -1)

        manager = Adw.StyleManager.get_default()
        current = manager.get_color_scheme()

        if current == Adw.ColorScheme.FORCE_LIGHT:
            selector.set_selected(1)
        elif current == Adw.ColorScheme.FORCE_DARK:
            selector.set_selected(2)
        else:
            selector.set_selected(0)

        selector.connect("notify::selected", self.on_theme_changed)
        return selector

    def on_theme_changed(self, selector, param):
        schemes = [
            Adw.ColorScheme.DEFAULT,
            Adw.ColorScheme.FORCE_LIGHT,
            Adw.ColorScheme.FORCE_DARK,
        ]

        selected = selector.get_selected()
        if selected < len(schemes):
            Adw.StyleManager.get_default().set_color_scheme(schemes[selected])

    # ---------------------------------------------------------
    # Shared UI helpers
    # ---------------------------------------------------------

    def make_header(self, title_text, subtitle_text=None):
        header = Adw.HeaderBar()

        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
        )

        title = Gtk.Label(label=title_text)
        title.add_css_class("heading")
        title_box.append(title)

        if subtitle_text:
            subtitle = Gtk.Label(label=subtitle_text)
            subtitle.add_css_class("dim-label")
            subtitle.add_css_class("caption")
            title_box.append(subtitle)

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

    def make_auth_page(self, heading, description):
        page = Adw.ToolbarView()
        page.add_top_bar(self.make_header("OIBSIP Chat"))

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scroll.set_vexpand(True)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(460)
        clamp.set_tightening_threshold(360)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )
        content.set_margin_top(36)
        content.set_margin_bottom(36)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_valign(Gtk.Align.CENTER)

        brand = Gtk.Label(label="OIBSIP")
        brand.add_css_class("brand-title")

        title = Gtk.Label(label=heading)
        title.add_css_class("title-1")
        title.set_wrap(True)

        subtitle = Gtk.Label(label=description)
        subtitle.add_css_class("dim-label")
        subtitle.set_wrap(True)
        subtitle.set_justify(Gtk.Justification.CENTER)

        content.append(brand)
        content.append(title)
        content.append(subtitle)

        clamp.set_child(content)
        scroll.set_child(clamp)
        page.set_content(scroll)

        return page, content

    def make_username_field(self, placeholder="Username"):
        entry = Gtk.Entry()
        entry.set_placeholder_text(placeholder)
        entry.set_hexpand(True)
        entry.set_activates_default(True)

        container = Gtk.ListBox()
        container.set_selection_mode(Gtk.SelectionMode.NONE)
        container.add_css_class("boxed-list")
        container.append(entry)

        return entry, container

    def make_status_label(self):
        label = Gtk.Label()
        label.add_css_class("dim-label")
        label.set_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        return label

    def make_primary_button(self, text, callback):
        button = Gtk.Button(label=text)
        button.add_css_class("suggested-action")
        button.add_css_class("pill")
        button.set_hexpand(True)
        button.connect("clicked", callback)
        return button

    def set_auth_busy(self, busy):
        for button in self.auth_buttons:
            button.set_sensitive(not busy)

    # ---------------------------------------------------------
    # Sign in and registration
    # ---------------------------------------------------------

    def show_login(self):
        self.messages_box = None
        self.chat_scroll = None
        self.message_entry = None
        page, content = self.make_auth_page(
            "Welcome back",
            "Sign in to continue your conversations.",
        )

        self.username, username_list = self.make_username_field()
        self.password, password_list = self.make_password_row("Password")
        self.status = self.make_status_label()

        self.login_button = self.make_primary_button(
            "Sign In",
            self.on_login,
        )

        register_button = Gtk.Button(label="Create an account")
        register_button.add_css_class("flat")
        register_button.connect(
            "clicked",
            lambda *_: self.show_register(),
        )

        content.append(username_list)
        content.append(password_list)
        content.append(self.status)
        content.append(self.login_button)
        content.append(register_button)

        self.auth_buttons = [self.login_button, register_button]
        self.window.set_content(page)
        self.window.set_default_widget(self.login_button)
        self.window.present()

    def show_register(self):
        page, content = self.make_auth_page(
            "Create your account",
            "A few details and you're ready to chat.",
        )

        self.register_username, username_list = self.make_username_field()
        self.register_password, password_list = self.make_password_row("Password")
        self.confirm_password, confirm_list = self.make_password_row("Confirm password")

        self.register_status = self.make_status_label()

        self.register_button = self.make_primary_button(
            "Create Account",
            self.on_register,
        )

        back_button = Gtk.Button(label="Back to sign in")
        back_button.add_css_class("flat")
        back_button.connect("clicked", lambda *_: self.show_login())

        hint = Gtk.Label(label="Use at least 8 characters for your password.")
        hint.add_css_class("dim-label")
        hint.add_css_class("caption")
        hint.set_wrap(True)

        content.append(username_list)
        content.append(password_list)
        content.append(confirm_list)
        content.append(hint)
        content.append(self.register_status)
        content.append(self.register_button)
        content.append(back_button)

        self.auth_buttons = [self.register_button, back_button]
        self.window.set_content(page)
        self.window.set_default_widget(self.register_button)
        self.window.present()

    def connect_client(self):
        if self.client and self.client.running:
            return

        self.client = ChatClient(on_message=self.receive_message)
        self.client.connect()

    def on_login(self, button):
        username = self.username.get_text().strip()
        password = self.password.get_text()

        if not username or not password:
            self.status.set_text("Enter your username and password.")
            return

        self.status.set_text("Connecting to the server…")
        self.set_auth_busy(True)

        try:
            self.connect_client()
            self.auth_action = "login"
            self.client.login(username, password)
        except (OSError, ConnectionError, ValueError) as exc:
            self.status.set_text(f"Connection failed: {exc}")
            self.set_auth_busy(False)

    def on_register(self, button):
        username = self.register_username.get_text().strip()
        password = self.register_password.get_text()
        confirmation = self.confirm_password.get_text()

        if not username or not password or not confirmation:
            self.register_status.set_text("Complete all fields.")
            return

        if len(username) > 32:
            self.register_status.set_text("Username must be at most 32 characters.")
            return

        if len(password) < 8:
            self.register_status.set_text(
                "Password must contain at least 8 characters."
            )
            return

        if password != confirmation:
            self.register_status.set_text("Passwords do not match.")
            return

        self.register_status.set_text("Creating your account…")
        self.set_auth_busy(True)

        try:
            self.connect_client()
            self.auth_action = "register"
            self.client.register(username, password)
        except (OSError, ConnectionError, ValueError) as exc:
            self.register_status.set_text(f"Connection failed: {exc}")
            self.set_auth_busy(False)

    # ---------------------------------------------------------
    # Socket events - update GTK only on its main thread
    # ---------------------------------------------------------

    def receive_message(self, message):
        GLib.idle_add(self.handle_message, message)

    def handle_message(self, message):
        kind = message.get("type")

        if kind == "auth":
            if not message.get("success"):
                error = message.get("text", "Authentication failed.")

                if self.auth_action == "register":
                    self.register_status.set_text(error)
                else:
                    self.status.set_text(error)

                self.set_auth_busy(False)
                return GLib.SOURCE_REMOVE

            if self.auth_action == "register":
                self.show_login()
                self.status.set_text(
                    "Account created. Sign in with your new credentials."
                )
                self.set_auth_busy(False)
                return GLib.SOURCE_REMOVE

            self.current_username = message.get(
                "username",
                self.username.get_text().strip(),
            )
            self.set_auth_busy(False)
            self.show_chat(self.current_username)
            return GLib.SOURCE_REMOVE

        if kind == "history":
            for item in message.get("messages", []):
                self.add_message(
                    item.get("username", "?"),
                    item.get("content", ""),
                    item.get("created_at", ""),
                )
            return GLib.SOURCE_REMOVE

        if kind == "chat":
            self.add_message(
                message.get("username", "?"),
                message.get("text", ""),
                message.get("time", ""),
            )

        elif kind == "system":
            self.add_system_message(message.get("text", ""))

        elif kind == "error":
            if self.status:
                self.status.set_text(message.get("text", "Something went wrong."))

        return GLib.SOURCE_REMOVE

    def make_account_menu(self):
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("avatar-default-symbolic")
        menu_button.set_tooltip_text("Account and session options")

        popover = Gtk.Popover()
        menu = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
        )
        menu.set_margin_top(10)
        menu.set_margin_bottom(10)
        menu.set_margin_start(10)
        menu.set_margin_end(10)

        account_label = Gtk.Label(
            label=f"Signed in as {self.current_username}",
            xalign=0,
        )
        account_label.add_css_class("dim-label")

        switch_button = Gtk.Button(label="Switch account")
        switch_button.add_css_class("flat")
        switch_button.connect(
            "clicked",
            lambda *_: self.sign_out(),
        )

        sign_out_button = Gtk.Button(label="Sign out")
        sign_out_button.add_css_class("flat")
        sign_out_button.connect(
            "clicked",
            lambda *_: self.sign_out(),
        )

        menu.append(account_label)
        menu.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        menu.append(switch_button)
        menu.append(sign_out_button)

        popover.set_child(menu)
        menu_button.set_popover(popover)
        return menu_button

    def sign_out(self):
        # Close the old session before showing the login page.
        client = self.client
        self.client = None

        if client:
            client.disconnect()

        self.current_username = ""
        self.messages_box = None
        self.chat_scroll = None
        self.message_entry = None

        self.show_login()

    # ---------------------------------------------------------
    # Main chat interface
    # ---------------------------------------------------------

    def show_chat(self, username):
        self.current_username = username
        self.messages_box = None

        page = Adw.ToolbarView()

        header = self.make_header(
            "General",
            f"Connected as {username}",
        )
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

        self.chat_scroll.set_child(self.messages_box)

        composer = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        composer.add_css_class("chat-composer")

        self.message_entry = Gtk.Entry()
        self.message_entry.set_placeholder_text("Message General…")
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

        self.window.set_default_size(1000, 700)
        self.window.set_content(page)
        self.window.set_default_widget(send_button)
        self.window.present()

    def add_message(self, username, text, timestamp=""):
        if self.messages_box is None:
            return

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

        row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0,
        )
        row.set_halign(Gtk.Align.CENTER)

        label = Gtk.Label(label=text)
        label.add_css_class("dim-label")
        label.add_css_class("caption")
        label.set_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)

        row.append(label)
        self.messages_box.append(row)
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

    def on_send(self, widget):
        if not self.client or not self.client.running:
            self.add_system_message("Not connected to the server.")
            return

        text = self.message_entry.get_text().strip()
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
