from mycroft.skills.core import FallbackSkill
from mycroft.util import camel_case_split
from jarbas_hive_mind import get_listener
from jarbas_hive_mind.configuration import CONFIGURATION
from jarbas_hive_mind.database import ClientDatabase
from twisted.internet import reactor


class HiveMindSkill(FallbackSkill):
    def __init__(self):
        super(HiveMindSkill, self).__init__(name='HiveMindSkill')
        # skill behaviour
        if "priority" not in self.settings:
            self.settings["priority"] = 50
        if "timeout" not in self.settings:
            self.settings["timeout"] = 15
        for k in CONFIGURATION:
            if k not in self.settings:
                self.settings[k] = CONFIGURATION[k]

        self._old_settings = dict(self.settings)

        # events
        self.settings_change_callback = self._on_web_settings_change
        self.namespace = "jarbas.hivemind"
        self.skill_name = camel_case_split(self.__class__.__name__)

    def initialize(self):
        # listen
        self.hivemind = get_listener(bus=self.bus)
        self.hivemind._autorun = False
        self.register_fallback(self.handle_fallback,
                               int(self.settings["priority"]))
        self.bus.on('mycroft.skills.initialized', self.run)

    # HiveMind
    def run(self, message):
        if self.settings["listen"]:
            self.settings["ssl"] = {"use_ssl": self.settings["use_ssl"]}
            self.hivemind.load_config(self.settings)
            self.hivemind.listen()
        reactor.run(installSignalHandlers=False)

    def authorize_client(self, name, access_key="RESISTENCEisFUTILE",
                         crypto_key="resistanceISfutile",
                         mail="placeholder@hivemind.com"):
        with ClientDatabase() as db:
            db.add_client(name, mail, access_key, crypto_key=crypto_key)

    def revoke_key(self, access_key="RESISTENCEisFUTILE"):
        with ClientDatabase() as db:
            db.delete_client(access_key)

    # setup
    def _on_web_settings_change(self):
        if self.settings["revoke_key"] and self.settings["access_key"] != \
                self._old_settings["access_key"]:
            self.revoke_key(self.settings["access_key"])
            self.speak_dialog("key_update")
        elif self.settings["add_key"] and self.settings["access_key"] != \
                self._old_settings["access_key"]:
            self.authorize_client(
                self.settings["client_name"],
                self.settings["access_key"],
                self.settings["crypto_key"]
            )
            self.speak_dialog("key_update")
        if self.settings["port"] != self._old_settings["port"] or \
                self.settings["listen"] != self._old_settings["listen"]:
            self.speak_dialog("need_reboot")
        self._old_settings = dict(self.settings)

    def get_intro_message(self):
        # welcome dialog on skill install
        self.speak_dialog("intro", {"skill_name": self.skill_name})

    # intents
    def handle_utterance(self, utterance):
        # TODO ask other hivemind
        return False

    # fallback
    def handle_fallback(self, message):
        utterance = message.data["utterance"]
        return self.handle_utterance(utterance)

    # shutdown
    def shutdown(self):
        self.hivemind.stop_from_thread()
        super(HiveMindSkill, self).shutdown()


def create_skill():
    return HiveMindSkill()
