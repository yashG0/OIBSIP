
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

from chat_app.client import ChatClient


class ChatApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.yash.OIBSIPChat")
        self.client = None
        self.auth_action = None
        self.window = None
        self.messages_box = None
        self.message_entry = None
        self.auth_buttons = []
        self.pending_registration = False

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("OIBSIP Chat")
        self.window.set_default_size(760, 620)
        self.window.set_size_request(360, 420)

        self.show_login()
        self.window.present()

    def make_auth_page(self, heading, description):
        page = Adw.ToolbarView()
        page.add_top_bar(Adw.HeaderBar())

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scroll.set_vexpand(True)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(440)
        clamp.set_tightening_threshold(360)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        content.set_margin_top(32)
        content.set_margin_bottom(32)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label(label=heading)
        title.add_css_class("title-1")
        title.set_wrap(True)

        subtitle = Gtk.Label(label=description)
        subtitle.add_css_class("dim-label")
        subtitle.set_wrap(True)
        subtitle.set_justify(Gtk.Justification.CENTER)

        content.append(title)
        content.append(subtitle)

        clamp.set_child(content)
        scroll.set_child(clamp)
        page.set_content(scroll)

        return page, content

    def make_password_row(self, title):
        row = Adw.PasswordEntryRow()
        row.set_title(title)

        container = Gtk.ListBox()
        container.set_selection_mode(Gtk.SelectionMode.NONE)
        container.add_css_class("boxed-list")
        container.append(row)

        return row, container

    def show_login(self):
        page, content = self.make_auth_page(
            "Welcome back",
            "Sign in to continue to OIBSIP Chat.",
        )

        self.username = Gtk.Entry()
        self.username.set_placeholder_text("Username")
        
        self.username.set_activates_default(True)

        username_list = Gtk.ListBox()
        username_list.set_selection_mode(Gtk.SelectionMode.NONE)
        username_list.add_css_class("boxed-list")
        username_list.append(self.username)

        self.password, password_list = self.make_password_row("Password")

        self.status = Gtk.Label()
        self.status.add_css_class("dim-label")
        self.status.set_wrap(True)
        self.status.set_justify(Gtk.Justification.CENTER)

        self.login_button = Gtk.Button(label="Sign In")
        self.login_button.add_css_class("suggested-action")
        self.login_button.add_css_class("pill")
        
        self.login_button.connect("clicked", self.on_login)

        create_link = Gtk.Button(label="Create an account")
        create_link.add_css_class("flat")
        create_link.connect("clicked", lambda *_: self.show_register())

        content.append(username_list)
        content.append(password_list)
        content.append(self.status)
        content.append(self.login_button)
        content.append(create_link)

        self.auth_buttons = [self.login_button, create_link]
        self.window.set_content(page)
        self.window.set_default_widget(self.login_button)
        self.window.present()

    def show_register(self):
        page, content = self.make_auth_page(
            "Create your account",
            "Choose a username and a password with at least 8 characters.",
        )

        self.register_username = Gtk.Entry()
        self.register_username.set_placeholder_text("Username")

        username_list = Gtk.ListBox()
        username_list.set_selection_mode(Gtk.SelectionMode.NONE)
        username_list.add_css_class("boxed-list")
        username_list.append(self.register_username)

        self.register_password, password_list = self.make_password_row(
            "Password"
        )
        self.confirm_password, confirm_list = self.make_password_row(
            "Confirm password"
        )

        self.register_status = Gtk.Label()
        self.register_status.add_css_class("dim-label")
        self.register_status.set_wrap(True)
        self.register_status.set_justify(Gtk.Justification.CENTER)

        self.register_button = Gtk.Button(label="Create Account")
        self.register_button.add_css_class("suggested-action")
        self.register_button.add_css_class("pill")
        self.register_button.connect("clicked", self.on_register)

        back_button = Gtk.Button(label="Back to sign in")
        back_button.add_css_class("flat")
        back_button.connect("clicked", lambda *_: self.show_login())

        content.append(username_list)
        content.append(password_list)
        content.append(confirm_list)
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

    def set_auth_busy(self, busy):
        for button in self.auth_buttons:
            button.set_sensitive(not busy)

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
            self.register_status.set_text(
                "Username must be at most 32 characters."
            )
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

    def receive_message(self, message):
        GLib.idle_add(self.handle_message, message)

    def handle_message(self, message):
        kind = message.get("type")

        if kind == "auth":
            if not message.get("success"):
                if self.auth_action == "register":
                    self.register_status.set_text(
                        message.get("text", "Registration failed.")
                    )
                else:
                    self.status.set_text(
                        message.get("text", "Sign in failed.")
                    )

                self.set_auth_busy(False)
                return GLib.SOURCE_REMOVE

            if self.auth_action == "register":
                self.show_login()
                self.status.set_text(
                    "Account created. Sign in with your new credentials."
                )
                self.password.set_text("")
                self.set_auth_busy(False)
                return GLib.SOURCE_REMOVE

            self.set_auth_busy(False)
            self.show_chat(message.get("username", ""))
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
            if hasattr(self, "status"):
                self.status.set_text(message.get("text", "An error occurred."))

        return GLib.SOURCE_REMOVE

    def show_chat(self, username):
        page = Adw.ToolbarView()
        header = Adw.HeaderBar()

        title = Gtk.Label(label=f"OIBSIP Chat · {username}")
        title.add_css_class("title")
        header.set_title_widget(title)

        page.add_top_bar(header)

        layout = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        layout.set_margin_top(12)
        layout.set_margin_bottom(12)
        layout.set_margin_start(16)
        layout.set_margin_end(16)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )

        self.messages_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        self.messages_box.set_margin_top(8)
        self.messages_box.set_margin_bottom(8)
        self.messages_box.set_margin_start(4)
        self.messages_box.set_margin_end(4)

        scroll.set_child(self.messages_box)

        composer = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        self.message_entry = Gtk.Entry()
        self.message_entry.set_placeholder_text("Write a message…")
        self.message_entry.set_hexpand(True)
        self.message_entry.set_activates_default(True)
        self.message_entry.connect("activate", self.on_send)

        send_button = Gtk.Button(label="Send")
        send_button.add_css_class("suggested-action")
        send_button.connect("clicked", self.on_send)

        composer.append(self.message_entry)
        composer.append(send_button)

        layout.append(scroll)
        layout.append(composer)
        page.set_content(layout)

        self.window.set_default_size(760, 600)
        self.window.set_content(page)
        self.window.set_default_widget(send_button)
        self.window.present()

    def add_message(self, username, text, timestamp=""):
        if self.messages_box is None:
            return

        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )
        card.add_css_class("card")
        card.set_margin_start(4)
        card.set_margin_end(4)

        heading = Gtk.Label(
            label=f"{username}  ·  {timestamp}",
            xalign=0,
        )
        heading.add_css_class("dim-label")

        body = Gtk.Label(label=text, xalign=0)
        body.set_wrap(True)
        body.set_selectable(True)
        body.set_max_width_chars(65)

        card.append(heading)
        card.append(body)
        self.messages_box.append(card)

    def add_system_message(self, text):
        if self.messages_box is None:
            return

        label = Gtk.Label(label=text)
        label.add_css_class("dim-label")
        label.set_wrap(True)
        self.messages_box.append(label)

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
