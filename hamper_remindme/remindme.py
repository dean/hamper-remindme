from collections import defaultdict
import datetime
import re
import time

from hamper.interfaces import ChatCommandPlugin, Command
from hamper.utils import ude

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

from twisted.internet import reactor


SQLAlchemyBase = declarative_base()


class Reminder(ChatCommandPlugin):
    """ Reminds a user in X minutes about Y. """

    name = 'remindme'

    priority = 1

    short_desc = 'Reminds user in X minutes with a message.'
    long_desc = ('!remindme <minutes> <message>'
                 '!cancel <message to cancel reminder for>')


    def setup(self, loader):
        super(Reminder, self).setup(loader)
        self.db = loader.db
        SQLAlchemyBase.metadata.create_all(self.db.engine)

    def remind(self, bot, user, message):
        reminder = self.db.session.query(ReminderTable).filter_by(
                                                    user=user,
                                                    message=message
                                                ).first()

        if not reminder.canceled:
            bot.notice(user, 'Reminder: ' + message)

        self.db.session.delete(reminder)
        self.db.session.commit()


    class RemindMe(Command):
        name = 'remindme'
        regex = r'^remindme (\d+) (.+)'

        short_desc = ('!remindme <minutes> <message>')

        def command(self, bot, comm, groups):
            print "intercepted remindme command"

            # reactor.callLater takes it's arguments as floats.
            duration, msg = self.parse_time(groups[0], groups[1])
            if duration == None:
                return

            db = self.plugin.db
            args = (bot, comm['user'], msg)
            reactor.callLater(duration, self.plugin.remind, *args)

            reminder = ReminderTable(user=comm['user'],
                                     message=msg)
            db.session.add(reminder)
            db.session.commit()

            # So we display in minutes.
            duration /= 60

            bot.reply(comm, "{0} has set a reminder to {1} in {2} minutes."
                                .format(comm['user'], msg, str(duration)))

        def parse_time(self, time, timestring):
                time = float(time)
                # Correct for any plurals
                words = timestring.split()
                validtimes = {
                    "second": 1,
                    "minute": 60,
                    "hour": 60 * 60,
                    "day": 60 * 60 * 24,
                    "week": 60 * 60 * 24 * 7,
                    "month": 60 * 60 * 24 * 7 * 4
                }
                word = words[0][:-1] if words[0].endswith('s') else words[0]
                mult = validtimes.get(word)
                if mult:
                    return (time * mult, ' '.join(words[1:]))
                else:
                    return (time * 60, timestring)

    class Cancel(Command):
        name = 'cancel'
        regex = r'^cancel \"(.+)\"$'

        short_desc = '!cancel <message> - cancel\'s a previous reminder.'

        def command(self, bot, comm, groups):
            print "intercepted cancel command!"
            db = self.plugin.db
            reminder = db.session.query(ReminderTable).filter_by(
                                                    user=comm['user'],
                                                    message=groups[0]
                                                ).first()
            if not reminder:
                bot.reply(comm, '{0}, that reminder doesn\'t exist!'.format(
                                                        comm['user']))

            reminder.cancel()
            db.session.commit()

            bot.reply(comm, "Reminder for {0} to \"{1}\" canceled.".format(
                                            comm['user'], groups[0]))


class ReminderTable(SQLAlchemyBase):
    """
    Model representing a reminder.
    """

    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True)
    user = Column(String(255))
    message = Column(String(1024))
    canceled = Column(Boolean)

    def __init__(self, user, message, canceled=False):
        self.user = user
        self.message = message
        self.canceled = canceled

    def cancel(self):
        self.canceled = True


remindme = Reminder()
