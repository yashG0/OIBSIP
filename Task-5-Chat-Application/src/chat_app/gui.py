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
        self.messages_box = None
        self.chat_scroll = None
        self.message_entry = None
        self.room_entry = None
        self.room_label = None
        self.status = None
        self.auth_buttons = []
        self.auth_action = "login"
        self.window_active = False
        self.css_provider = None

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("OIBSIP Chat")
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
                font-size: 28px;
                font-weight: 800;
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

    def show_login(self):
        self.messages_box = None
        self.message_entry = None
        self.room_entry = None
        self.auth_action = "login"
        self.auth_buttons = []

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
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )
        content.set_margin_top(36)
        content.set_margin_bottom(36)
        content.set_margin_start(24)
        content.set_margin_end(24)

        brand = Gtk.Label(label="OIBSIP")
        brand.add_css_class("brand-title")
        heading = Gtk.Label(label="Welcome back")
        heading.add_css_class("title-1")
        description = Gtk.Label(label="Sign in or create an account to chat.")
        description.add_css_class("dim-label")
        description.set_wrap(True)

        self.username, username_list = self.make_username_field()
        self.password, password_list = self.make_password_row("Password")
        self.status = self.make_status_label()

        login_button = self.make_button("Sign in", self.on_login, primary=True)
        register_button = self.make_button("Create account", self.on_register)
        self.auth_buttons = [login_button, register_button]

        content.append(brand)
        content.append(heading)
        content.append(description)
        content.append(username_list)
        content.append(password_list)
        content.append(login_button)
        content.append(register_button)
        content.append(self.status)

        clamp.set_child(content)
        scroll.set_child(clamp)
        page.set_content(scroll)
        self.window.set_content(page)

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
        if not self.ensure_connected():
            return
        self.auth_action = "register"
        self.set_auth_busy(True)
        try:
            self.client.register(
                self.username.get_text().strip(),
                self.password.get_text(),
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
        self.show_login()

    def make_account_menu(self):
        button = Gtk.MenuButton()
        button.set_icon_name("avatar-default-symbolic")
        button.set_tooltip_text("Account options")

        popover = Gtk.Popover()
        menu = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
        )
        menu.set_margin_top(10)
        menu.set_margin_bottom(10)
        menu.set_margin_start(10)
        menu.set_margin_end(10)

        account = Gtk.Label(label=f"Signed in as {self.current_username}")
        account.add_css_class("dim-label")
        logout = Gtk.Button(label="Sign out")
        logout.connect("clicked", self.sign_out)

        menu.append(account)
        menu.append(logout)
        popover.set_child(menu)
        button.set_popover(popover)
        return button

    def show_chat(self, username):
        self.current_username = username
        self.current_room = "general"

        page = Adw.ToolbarView()
        header = self.make_header("General", f"Connected as {username}")
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

        room_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        self.room_label = Gtk.Label(label="Room: #general")
        self.room_entry = Gtk.Entry()
        self.room_entry.set_placeholder_text("Room name")
        self.room_entry.set_hexpand(True)

        create_button = Gtk.Button(label="Create")
        create_button.connect("clicked", self.create_room)
        join_button = Gtk.Button(label="Join")
        join_button.connect("clicked", self.join_room)

        room_bar.append(self.room_label)
        room_bar.append(self.room_entry)
        room_bar.append(create_button)
        room_bar.append(join_button)

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

        layout.append(room_bar)
        layout.append(self.chat_scroll)
        layout.append(composer)
        page.set_content(layout)
        self.window.set_content(page)
        self.window.set_default_widget(send_button)
        self.window.present()

    def create_room(self, *_):
        room = self.room_entry.get_text().strip()
        if not room or not self.client or not self.client.running:
            return
        try:
            self.client.create_room(room)
        except (OSError, ConnectionError, ValueError) as exc:
            self.add_system_message(str(exc))

    def join_room(self, *_):
        room = self.room_entry.get_text().strip()
        if not room or not self.client or not self.client.running:
            return
        try:
            self.client.join_room(room)
        except (OSError, ConnectionError, ValueError) as exc:
            self.add_system_message(str(exc))

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
            self.current_room = message.get("room", "general")
            self.set_auth_busy(False)
            self.show_chat(self.current_username)
            return GLib.SOURCE_REMOVE

        if kind == "room_created":
            self.add_system_message(message.get("text", "Room created."))
            return GLib.SOURCE_REMOVE

        if kind == "room_joined":
            self.current_room = message.get("room", "general")
            if self.room_label:
                self.room_label.set_text(f"Room: #{self.current_room}")
            if self.message_entry:
                self.message_entry.set_placeholder_text(
                    f"Message #{self.current_room}…"
                )
            if self.messages_box:
                while child := self.messages_box.get_first_child():
                    self.messages_box.remove(child)
            self.add_system_message(f"Joined #{self.current_room}")
            return GLib.SOURCE_REMOVE

        if kind == "history":
            if self.messages_box:
                while child := self.messages_box.get_first_child():
                    self.messages_box.remove(child)
            for item in message.get("messages", []):
                self.add_message(
                    item.get("username", "?"),
                    item.get("content", ""),
                    item.get("created_at", ""),
                )
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
