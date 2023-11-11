# for type references to own class
# https://stackoverflow.com/a/33533514
from __future__ import annotations

import asyncio
import os
from typing import List
import datetime
import random
import time

import discord
import pytz
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import models
from django.forms import model_to_dict
from django.utils import timezone
from dateutil.tz import tz


TIME_ZONE = 'Canada/Pacific'
PACIFIC_TZ = tz.gettz(TIME_ZONE)

from .customFields import GeneratedIdentityField
import requests


class BanRecord(models.Model):
    ban_id = GeneratedIdentityField(primary_key=True)
    username = models.CharField(max_length=37, null=False)
    user_id = models.BigIntegerField(null=False)
    mod = models.CharField(max_length=37, null=True)
    mod_id = models.BigIntegerField(null=True)
    ban_date = models.BigIntegerField(null=True)
    reason = models.CharField(max_length=512, null=False)
    unban_date = models.BigIntegerField(null=True, default=None)

    class Meta:
        db_table = 'wall_e_models_ban_records'

    @classmethod
    @sync_to_async
    def insert_records(cls, records: List[BanRecord]) -> None:
        """Adds entry to BanRecord table"""
        BanRecord.objects.bulk_create(records)

    @classmethod
    @sync_to_async
    def insert_record(cls, record: BanRecord) -> None:
        """Adds entry to BanRecord table"""
        record.save()

    @classmethod
    @sync_to_async
    def get_all_active_ban_user_ids(cls) -> List[int]:
        """Returns list of user_ids for all currently banned users"""

        return list(BanRecord.objects.values_list('user_id', flat=True).filter(unban_date=None))

    @classmethod
    @sync_to_async
    def get_all_active_bans(cls) -> List[BanRecord]:
        """Returns list of usernames and user_ids for all currently banned users"""

        return list(BanRecord.objects.values('username', 'user_id').filter(unban_date=None))

    @classmethod
    @sync_to_async
    def get_active_bans_count(cls) -> int:
        """Returns count of all the active bans"""

        return BanRecord.objects.filter(unban_date=None).count()

    @classmethod
    @sync_to_async
    def unban_by_id(cls, user_id: int) -> str:
        """Set active=False for user with the given user_id. This representes unbanning a user."""
        try:
            user = BanRecord.objects.get(user_id=user_id, unban_date=None)
        except Exception:
            return None

        user.unban_date = datetime.datetime.now().timestamp()
        user.save()
        return user.username

    @classmethod
    @sync_to_async
    def user_is_banned(cls, user_id) -> bool:
        return BanRecord.objects.all().filter(user_id=user_id).first() is not None

    def __str__(self) -> str:
        return f"ban_id=[{self.ban_id}] username=[{self.username}] user_id=[{self.user_id}] " \
               f"mod=[{self.mod}] mod_id=[{self.mod_id}] date=[{self.ban_date}] reason=[{self.reason}]" \
               f"unban_date=[{self.unban_date}]"


class CommandStat(models.Model):
    epoch_time = models.BigAutoField(
        primary_key=True
    )
    year = models.IntegerField(
        default=timezone.now
    )
    month = models.IntegerField(
        default=timezone.now
    )
    day = models.IntegerField(
        default=timezone.now
    )
    hour = models.IntegerField(
        default=timezone.now
    )
    channel_name = models.CharField(
        max_length=2000,
        default='NA'
    )
    command = models.CharField(
        max_length=2000
    )
    invoked_with = models.CharField(
        max_length=2000
    )
    invoked_subcommand = models.CharField(
        max_length=2000,
        blank=True, null=True
    )

    @classmethod
    def get_column_headers_from_database(cls):
        return [key for key in model_to_dict(CommandStat) if key != "epoch_time"]

    @classmethod
    @sync_to_async
    def get_all_entries(cls):
        return list(CommandStat.objects.all())

    @classmethod
    @sync_to_async
    def save_command_stat(cls, command_stat):
        while True:
            try:
                command_stat.save()
                return
            except Exception:
                command_stat.epoch_time += 1

    @classmethod
    async def get_command_stats_dict(cls, filters=None):
        filter_stats_dict = {}
        for command_stat in await CommandStat.get_all_entries():
            command_stat = model_to_dict(command_stat)
            key = ""
            for idx, command_filter in enumerate(filters):
                key += f"{command_stat[command_filter]}"
                if idx + 1 < len(filters):
                    key += "-"
            filter_stats_dict[key] = filter_stats_dict.get(key, 0) + 1
        return filter_stats_dict

    def __str__(self):
        return \
            f"{self.epoch_time} - {self.command} as invoked with {self.invoked_with} with " \
            f"subcommand {self.invoked_subcommand} and year {self.year}, " \
            f"month {self.month} and hour {self.hour}"

    def save(self, *args, **kwargs):
        if type(self.year) == datetime.datetime:
            self.year = self.year.year
        if type(self.month) == datetime.datetime:
            self.month = self.month.month
        if type(self.day) == datetime.datetime:
            self.day = self.day.day
        if type(self.hour) == datetime.datetime:
            self.hour = self.hour.hour
        super(CommandStat, self).save(*args, **kwargs)


class UserPoint(models.Model):
    user_id = models.PositiveBigIntegerField(
        unique=True
    )
    name = models.CharField(
        max_length=500,
        default=None,
        null=True
    )
    nickname = models.CharField(
        max_length=500,
        default=None,
        null=True
    )
    avatar_url = models.CharField(
        max_length=1000,
        default=None,
        null=True
    )
    leveling_message_avatar_url = models.CharField(
        max_length=1000,
        default=None,
        null=True
    )
    avatar_url_message_id = models.PositiveBigIntegerField(
        default=None,
        null=True
    )
    points = models.PositiveBigIntegerField(

    )
    level_up_specific_points = models.PositiveBigIntegerField(

    )
    message_count = models.PositiveBigIntegerField(

    )
    latest_time_xp_was_earned_epoch = models.BigIntegerField(
        default=0
    )
    level_number = models.PositiveBigIntegerField(

    )
    hidden = models.BooleanField(
        default=False
    )
    leveling_update_needed = models.BooleanField(
        default=True
    )
    leveling_update_attempt = models.IntegerField(
        default=0,
        null=False
    )
    deleted_member = models.BooleanField(
        default=False
    )

    @sync_to_async
    def async_save(self):
        self.save()

    @sync_to_async
    def async_bulk_update(self, users):
        UserPoint.objects.bulk_update(
            users,
            ["nickname", 'name', 'avatar_url', 'leveling_message_avatar_url',
             'avatar_url_message_id']
        )

    @staticmethod
    @sync_to_async
    def create_user_point(
            user_id, points=random.randint(15, 25), message_count=1,
            latest_time_xp_was_earned=datetime.datetime.now(), level=0):
        user_point = UserPoint(
            user_id=user_id, points=points,
            level_up_specific_points=UserPoint.calculate_level_up_specific_points(points),
            message_count=message_count,
            latest_time_xp_was_earned_epoch=latest_time_xp_was_earned.timestamp(), level_number=level
        )
        user_point.save()
        return user_point

    @classmethod
    def calculate_level_up_specific_points(cls, points):
        indx = 0
        levels = Level.objects.all().order_by('total_points_required')
        while levels[indx].xp_needed_to_level_up_to_next_level < points and indx < len(levels):
            points -= levels[indx].xp_needed_to_level_up_to_next_level
            indx += 1

        return points

    @sync_to_async
    def increment_points(self):
        alert_user = False
        if self.message_counts_towards_points():
            point = random.randint(15, 25)
            self.points += point
            self.level_up_specific_points += point
            self.message_count += 1
            if self.level_number < 100:
                current_level = Level.objects.get(number=self.level_number)
                if self.level_up_specific_points >= current_level.xp_needed_to_level_up_to_next_level:
                    self.level_up_specific_points -= current_level.xp_needed_to_level_up_to_next_level
                    self.level_number += 1
                    alert_user = True
            self.latest_time_xp_was_earned_epoch = datetime.datetime.now().timestamp()
            self.save()
        return alert_user

    @sync_to_async
    def get_rank(self):
        users_above_in_rank = []
        for user in UserPoint.objects.all().order_by('-points'):
            if user.user_id != self.user_id:
                users_above_in_rank.append(user)
            else:
                return len(users_above_in_rank)+1
        return len(users_above_in_rank)+1

    @sync_to_async
    def get_xp_needed_to_level_up_to_next_level(self):
        return Level.objects.get(number=self.level_number).xp_needed_to_level_up_to_next_level

    @sync_to_async
    def hide_xp(self):
        self.hidden = True
        self.save()

    @sync_to_async
    def show_xp(self):
        self.hidden = False
        self.save()

    @staticmethod
    @sync_to_async
    def user_points_have_been_imported():
        return len(list(UserPoint.objects.all()[:1])) == 1

    @staticmethod
    @sync_to_async
    def clear_all_entries():
        UserPoint.objects.all().delete()

    def message_counts_towards_points(self):
        return datetime.datetime.fromtimestamp(
            self.latest_time_xp_was_earned_epoch,
            pytz.timezone(settings.TIME_ZONE)
        ) + datetime.timedelta(minutes=1) < datetime.datetime.now(tz=pytz.timezone(settings.TIME_ZONE))

    @staticmethod
    @sync_to_async
    def load_to_dict():
        return {user_point.user_id: user_point for user_point in UserPoint.objects.all().order_by('-points')}


    @staticmethod
    @sync_to_async
    def get_users_that_need_leveling_info_updated(top: int = None):
        query = UserPoint.objects.all().filter(
                leveling_update_needed=True, deleted_member=False, leveling_update_attempt__lt=5
            ).order_by('-points')
        if top is not None:
            query = query[:top]
        return list(query.values_list('user_id', flat=True))

    @staticmethod
    @sync_to_async
    def get_number_of_users_that_need_leveling_info_updated():
        return UserPoint.objects.all().filter(
                leveling_update_needed=True, deleted_member=False, leveling_update_attempt__lt=5
            ).count()

    async def update_leveling_profile_info(self, logger, member, levelling_website_avatar_channel):
        avatar_file_name = 'levelling-avatar.png'
        try:
            self.leveling_update_attempt += 1
            user_point_changed = False
            if self.avatar_url != member.display_avatar.url:
                if self.avatar_url_message_id is not None:
                    avatar_msg = await levelling_website_avatar_channel.fetch_message(
                        self.avatar_url_message_id
                    )
                    await avatar_msg.delete()
                with open(avatar_file_name, "wb") as file:
                    file.write(requests.get(member.display_avatar.url).content)
                avatar_msg = await levelling_website_avatar_channel.send(
                    file=discord.File(avatar_file_name)
                )
                os.remove(avatar_file_name)
                self.avatar_url = member.display_avatar.url
                self.leveling_message_avatar_url = avatar_msg.attachments[0].url
                self.avatar_url_message_id = avatar_msg.id
                user_point_changed = True
            user_point_changed = user_point_changed or self.nickname != member.nick
            user_point_changed = user_point_changed or self.name != member.name
            if user_point_changed:
                self.nickname = member.nick
                self.name = member.name
                self.leveling_update_needed = False
                self.leveling_update_attempt = 0
                await self.async_save()
        except Exception as e:
            logger.error(
                "[wall_e_models models.py update_leveling_profile_info()] experienced following error when trying to "
                f"update the profile info for {member}\n{e}"
            )
            await asyncio.sleep(5)
            await self.async_save()
            if os.path.exists(avatar_file_name):
                os.remove(avatar_file_name)
            raise Exception(e)

    async def mark_ready_for_levelling_profile_update(self, member):
        user_profile_data_changed = (
            self.nickname != member.nick or self.name != member.name or self.avatar_url != member.display_avatar.url
        )
        if user_profile_data_changed:
            self.leveling_update_needed = True
            self.deleted_member = False
            self.leveling_update_attempt = 0
            await self.async_save()

class Level(models.Model):
    number = models.PositiveBigIntegerField(
        unique=True
    )  # xp_level
    total_points_required = models.PositiveBigIntegerField(

    )  # xp_level_points_required

    xp_needed_to_level_up_to_next_level = models.PositiveBigIntegerField(

    )

    role_id = models.PositiveBigIntegerField(
        null=True,
        unique=True
    )
    role_name = models.CharField(
        max_length=500,
        null=True,
        unique=True
    )  # xp_role_name

    @staticmethod
    @sync_to_async
    def create_level(number, total_points_required, xp_needed_to_level_up_to_next_level,
                     role_id=None, role_name=None):
        level = Level(
            number=number, total_points_required=total_points_required,
            xp_needed_to_level_up_to_next_level=xp_needed_to_level_up_to_next_level,
            role_id=role_id, role_name=role_name
        )
        level.save()
        return level

    @sync_to_async
    def async_save(self):
        self.save()

    @staticmethod
    @sync_to_async
    def level_points_have_been_imported():
        return len(list(Level.objects.all()[:1])) == 1

    @staticmethod
    @sync_to_async
    def clear_all_entries():
        Level.objects.all().delete()

    @staticmethod
    @sync_to_async
    def load_to_dict():
        return {level.number: level for level in Level.objects.all()}

    @sync_to_async
    def set_level_name(self, new_role_name, role_id):
        self.role_name = new_role_name
        self.role_id = role_id
        self.save()

    @sync_to_async
    def rename_level_name(self, new_role_name):
        self.role_name = new_role_name
        self.save()

    @sync_to_async
    def remove_role(self):
        self.role_name = None
        self.role_id = None
        self.save()


class Reminder(models.Model):
    id = models.BigAutoField(
        primary_key=True
    )
    reminder_date_epoch = models.BigIntegerField(
        default=0
    )
    message = models.CharField(
        max_length=2000,
        default="INVALID"
    )
    author_id = models.BigIntegerField(
        default=0
    )

    def __str__(self):
        return f"Reminder for user {self.author_id} on date {self.reminder_date_epoch} with message {self.message}"

    @classmethod
    @sync_to_async
    def get_expired_reminders(cls):
        return list(
            Reminder.objects.all().filter(
                reminder_date_epoch__lte=datetime.datetime.now(
                    tz=pytz.timezone(f"{settings.TIME_ZONE}")
                ).timestamp()
            )
        )

    @classmethod
    @sync_to_async
    def get_reminder_by_id(cls, reminder_id):
        if not f"{reminder_id}".isdigit():
            return None
        reminders = Reminder.objects.all().filter(id=reminder_id)
        if len(reminders) == 0:
            return None
        else:
            return reminders[0]


    @classmethod
    @sync_to_async
    def delete_reminder_by_id(cls, reminder_to_delete):
        Reminder.objects.all().get(id=reminder_to_delete).delete()

    @classmethod
    @sync_to_async
    def delete_reminder(cls, reminder_to_delete):
        reminder_to_delete.delete()

    @classmethod
    @sync_to_async
    def get_reminder_by_author(cls, author_id):
        return list(Reminder.objects.all().filter(author_id=author_id).order_by('reminder_date_epoch'))


    @classmethod
    @sync_to_async
    def get_all_reminders(cls):
        return list(Reminder.objects.all().order_by('reminder_date_epoch'))


    @classmethod
    @sync_to_async
    def save_reminder(cls, reminder_to_save):
        reminder_to_save.save()

    def get_countdown(self):
        seconds = int(self.reminder_date_epoch - time.time())
        day = seconds // (24 * 3600)
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        message = "Reminder set for "
        if day > 0:
            message += f" {day} days"
        if hour > 0:
            message += f" {hour} hours"
        if minutes > 0:
            message += f" {minutes} minutes"
        if seconds > 0:
            message += f" {seconds} seconds"
        return f"{message} from now"


class HelpMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    message_id = models.BigIntegerField(null=False)
    channel_name = models.CharField(max_length=500, default=None, null=True)
    channel_id = models.BigIntegerField(null=False)
    help_message_expiration_date = models.BigIntegerField(default=0)
    time_created = models.BigIntegerField(default=0)

    @property
    def get_expiration_date_pst(self):
        return convert_utc_time_to_pacific(datetime.datetime.fromtimestamp(self.help_message_expiration_date))

    @property
    def get_pst_date_message_created(self):
        return convert_utc_time_to_pacific(datetime.datetime.fromtimestamp(self.time_created))

    @classmethod
    @sync_to_async
    def insert_record(cls, record: HelpMessage) -> None:
        """Adds entry to HelpMessage table"""
        record.save()

    @classmethod
    @sync_to_async
    def delete_message(cls, help_message_record_to_delete):
        help_message_record_to_delete.delete()

    @classmethod
    @sync_to_async
    def get_messages_to_delete(cls):
        return list(
            HelpMessage.objects.all().filter(
                help_message_expiration_date__lte=convert_utc_time_to_pacific(datetime.datetime.now()).timestamp()
            )
        )

    def save(self, *args, **kwargs):
        self.help_message_expiration_date = (
            convert_utc_time_to_pacific(datetime.datetime.now()) + datetime.timedelta(minutes=1)
        ).timestamp()
        super(HelpMessage, self).save(*args, **kwargs)

    def __str__(self):
        return (
            f"[HelpMessage {self.id} for channel #{self.channel_name}({self.channel_id}) and message "
            f"{self.message_id} that was created on"
            f" {self.get_pst_date_message_created.strftime('%Y %b %-d %I:%M:%S %p %Z')}]"
        )


def convert_utc_time_to_pacific(utc_datetime):
    """
    Convert the given UTC timezone object to a PST timezone object

    Keyword Arguments
    utc_datetime -- the given UTC timezone object to convert

    Return
    datetime -- the PST timezone equivalent of the utc_datetime
    """
    return utc_datetime.astimezone(PACIFIC_TZ)


class EmbedAvatar(models.Model):
    avatar_discord_url = models.CharField(
        max_length=5000
    )
    avatar_discord_permanent_url = models.CharField(
        max_length=5000
    )

    @classmethod
    @sync_to_async
    def insert_record(cls, record: EmbedAvatar) -> None:
        """Adds entry to EmbedAvatar table"""
        record.save()

    @classmethod
    @sync_to_async
    def get_avatar_by_url(cls, url):
        avatars = EmbedAvatar.objects.all().filter(avatar_discord_url=url)
        if len(avatars) == 0:
            return None
        else:
            return avatars[0]
