import os
import logging
import threading

from slacker import Slacker

class Slack():
    
    _slack = None
    _slack_token = os.getenv("SLACK_TOKEN", None)
    _slack_authed = None
    _slack_channel = os.getenv("SLACK_CHANNEL", "#test")
    
    @staticmethod
    def slack(text, attachments):
        assert not text or isinstance(text, str)
        assert not attachments or isinstance(attachments, list)
        assert text or attachments
        
        if Slack._slack_authed is None or Slack._slack is None:
            Slack._slack = Slacker(os.getenv("SLACK_TOKEN"))
            try:
                auth = Slack._slack.auth.test()
                if auth.successful:
                    logging.info("[{}] Slack authorized as \"{}\" as part of the team \"{}\"".format(threading.get_ident(), auth.body.get("user"), auth.body.get("team")))
                    Slack._slack_authed = True
                else:
                    logging.warn("[{}] Failed to authorize to Slack".format(threading.get_ident()))
                    Slack._slack_authed = False
                
            except Exception:
                logging.exception("[{}] Failed to authorize to Slack".format(threading.get_ident()))
                Slack._slack_authed = False
        
        if Slack._slack_authed is not True:
            logging.warn("[{}] Not authorized to send messages to Slack".format(threading.get_ident()))
        
        Slack._slack.chat.post_message(channel=Slack._slack_channel, as_user=True, text=text, attachments=attachments)