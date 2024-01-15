# for type references to own class
# https://stackoverflow.com/a/33533514
from __future__ import annotations

import asyncio
import os
import re
import time
from typing import List
import datetime
import random

import discord
import pytz
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.forms import model_to_dict
from django.utils import timezone
from dateutil.tz import tz

from .pstdatetime import PSTDateTimeField

TIME_ZONE = 'Canada/Pacific'
PACIFIC_TZ = tz.gettz(TIME_ZONE)

from .customFields import GeneratedIdentityField  # noqa: E402
import requests  # noqa: E402


class BanRecord(models.Model):
    ban_id = GeneratedIdentityField(primary_key=True)
    username = models.CharField(max_length=37, null=False)
    user_id = models.BigIntegerField(null=False)
    mod = models.CharField(max_length=37, null=True)
    mod_id = models.BigIntegerField(null=True)
    epoch_ban_date = models.BigIntegerField(null=True)
    # ban_date = PSTDateTimeField(default=timezone.now)
    reason = models.CharField(max_length=512, null=False)
    epoch_unban_date = models.BigIntegerField(null=True, default=None)
    # unban_date = PSTDateTimeField(null=True, default=None)
    is_purged = models.BooleanField(default=False) # need to be changed to False after first migration
    purge_window_days = models.IntegerField(default=1)

    class Meta:
        db_table = 'wall_e_models_ban_records'
        constraints = [
            UniqueConstraint(fields=['user_id'], name='unique_active_ban', condition=Q(epoch_unban_date__isnull=True))
        ]

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
    def get_all_active_ban_user_ids(cls) -> dict:
        """Returns a dict of user_ids for all currently banned users"""
        return {
            user['user_id']: user['username']
            for user in list(BanRecord.objects.filter(epoch_unban_date=None).values('user_id', 'username'))
        }

    @classmethod
    @sync_to_async
    def get_all_active_bans(cls, search_query=None) -> List[BanRecord]:
        """Returns list of usernames and user_ids for all currently banned users"""
        bans = BanRecord.objects.filter(epoch_unban_date=None).order_by('-epoch_ban_date').values('username', 'user_id')
        if search_query is not None:
            bans = bans.filter(
                Q(username__icontains=search_query) | Q(user_id__contains=search_query)
            )
        return list(bans)

    @classmethod
    @sync_to_async
    def get_active_bans_count(cls) -> int:
        """Returns count of all the active bans"""

        return BanRecord.objects.filter(epoch_unban_date=None).count()

    @classmethod
    @sync_to_async
    def unban_by_id(cls, user_id: int) -> str | None:
        """Set active=False for user with the given user_id. This represents unbanning a user."""
        try:
            user = BanRecord.objects.get(user_id=user_id, epoch_unban_date=None)
        except Exception:
            return None

        user.epoch_unban_date = datetime.datetime.now().timestamp()
        user.save()
        return user.username

    @classmethod
    @sync_to_async
    def user_is_banned(cls, user_id) -> bool:
        return BanRecord.objects.all().filter(user_id=user_id).first() is not None

    @classmethod
    @sync_to_async
    def get_unpurged_users(cls) -> List[BanRecord]:
        return list(BanRecord.objects.all().filter(is_purged=False))

    def __str__(self) -> str:
        return f"ban_id=[{self.ban_id}] username=[{self.username}] user_id=[{self.user_id}] " \
               f"mod=[{self.mod}] mod_id=[{self.mod_id}] date=[{self.epoch_ban_date}] reason=[{self.reason}]" \
               f"epoch_unban_date=[{self.epoch_unban_date}]"


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


class ProfileBucketInProgress(models.Model):
    bucket_number_completed = models.IntegerField(
        default=None,
        null=True
    )

    @staticmethod
    @sync_to_async
    def retrieve_entry():
        return ProfileBucketInProgress.objects.all().first()

    @staticmethod
    @sync_to_async
    def create_entry():
        profile_bucket_in_progress = ProfileBucketInProgress(bucket_number_completed=1)
        profile_bucket_in_progress.save()
        return profile_bucket_in_progress

    @staticmethod
    @sync_to_async
    def async_save(profile_bucket_in_progress):
        profile_bucket_in_progress.save()


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
    leveling_update_attempt = models.IntegerField(
        default=0,
        null=False
    )
    # there needed to be a way to regularly check all the user's profiles to ensure the leaderboard website was as
    # up-to-date as possible. At the time of making this comment, the CSSS discord guild has just a bit over 7000
    # members, which seemed like a bad idea to start calling the discord API for 7000 users in a short burst of time
    # a bad idea as well as a bad idea to bulk_update that many people. To combat this, I decided to use the
    # pigeonhole principle when spreading the load of when to update the users. This is implemented in
    # set_bucket_numbers in wall_e
    bucket_number = models.IntegerField(
        default=None,
        null=True
    )

    @sync_to_async
    def async_save(self):
        self.save()

    @sync_to_async
    def async_bulk_update(self, users, objects_to_update):
        UserPoint.objects.bulk_update(users, objects_to_update)

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
        index = 0
        levels = Level.objects.all().order_by('total_points_required')
        while levels[index].xp_needed_to_level_up_to_next_level < points and index < len(levels):
            points -= levels[index].xp_needed_to_level_up_to_next_level
            index += 1

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

    def message_counts_towards_points(self):
        return datetime.datetime.fromtimestamp(
            self.latest_time_xp_was_earned_epoch,
            pytz.timezone(settings.TIME_ZONE)
        ) + datetime.timedelta(minutes=1) < datetime.datetime.now(tz=pytz.timezone(settings.TIME_ZONE))

    @staticmethod
    @sync_to_async
    def load_to_cache():
        return {user_point.user_id: user_point for user_point in UserPoint.objects.all().order_by('-points')}

    @staticmethod
    @sync_to_async
    def get_users_that_need_leveling_info_updated(bucket_number):
        query = UserPoint.objects.all().filter(bucket_number=bucket_number).order_by('-points')
        return list(query.values_list('user_id', flat=True))

    async def update_leveling_profile_info(self, logger, member, levelling_website_avatar_channel,
                                           updated_user_log_id=None):
        user_updated = False
        if not re.match(r"Deleted User \w*$", member.name):
            file_name_friendly_member_name = member.name.replace("/", "").replace("\\", "")
            avatar_file_name = f'levelling-avatar-{file_name_friendly_member_name}-{time.time()}.png'
            try:
                self.leveling_update_attempt += 1
                changes_detected = ""
                avatar_changed = self.avatar_url != member.display_avatar.url
                name_changed = self.name != member.name
                number_of_changes = 0
                if avatar_changed:
                    number_of_changes += 1
                    changes_detected = "avatar"
                if type(member) == discord.Member:  # necessary because if the user is no longer in the Guild,
                    # then they don't have a nickname on it
                    if self.nickname != member.nick:
                        number_of_changes += 1
                        if changes_detected:
                            changes_detected += ", " if name_changed else " and "
                        changes_detected += "nickname"
                if name_changed:
                    if changes_detected:
                        if number_of_changes == 2:
                            changes_detected += ","
                        changes_detected += " and "
                    changes_detected += "name"
                    number_of_changes += 1
                if avatar_changed:
                    if self.avatar_url_message_id is not None:
                        avatar_msg = await levelling_website_avatar_channel.fetch_message(
                            self.avatar_url_message_id
                        )
                        await avatar_msg.delete()
                        logger.debug(
                            f"[wall_e_models models.py update_leveling_profile_info()] deleted old avatar message for "
                            f"member {member}"
                        )
                    with open(avatar_file_name, "wb") as file:
                        file.write(requests.get(member.display_avatar.url).content)
                    avatar_msg = await levelling_website_avatar_channel.send(
                        file=discord.File(avatar_file_name)
                    )
                    os.remove(avatar_file_name)
                    self.avatar_url = member.display_avatar.url
                    self.leveling_message_avatar_url = avatar_msg.attachments[0].url
                    self.avatar_url_message_id = avatar_msg.id
                if number_of_changes > 0:
                    logger.debug(
                        f"[wall_e_models models.py update_leveling_profile_info()] detected {changes_detected}"
                        f" change for member {member}"
                    )
                    self.nickname = member.nick if type(member) == discord.Member else None
                    self.name = member.name
                    self.leveling_update_attempt = 0
                    user_updated = True
                    await self.async_save()
                if updated_user_log_id is not None:
                    await UpdatedUser.async_delete(updated_user_log_id)
            except Exception as e:
                logger.error(
                    "[wall_e_models models.py update_leveling_profile_info()] experienced following error when "
                    f"trying to update the profile info for {member}\n{e}"
                )
                await asyncio.sleep(5)
                await self.async_save()
                if os.path.exists(avatar_file_name):
                    os.remove(avatar_file_name)
                raise Exception(e)
        return user_updated


class UpdatedUser(models.Model):
    user_point = models.ForeignKey(
        UserPoint, on_delete=models.CASCADE
    )

    @staticmethod
    @sync_to_async
    def get_updated_user_logs(top: int = None):
        query = UpdatedUser.objects.all()
        if top is not None:
            query = query[:top]
        return list(query.values_list('id', 'user_point__user_id'))

    @sync_to_async
    def async_save(self):
        self.save()

    @staticmethod
    @sync_to_async
    def async_delete(async_delete):
        UpdatedUser.objects.get(id=async_delete).delete()

    @staticmethod
    @sync_to_async
    def outdated_user_profile(member):
        exclusion_filter = Q(avatar_url=member.display_avatar.url) & Q(name=member.name)
        if type(member) == discord.Member:
            exclusion_filter = exclusion_filter & Q(nickname=member.nick)
        return UserPoint.objects.filter(user_id=member.id).exclude(exclusion_filter).first()


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
    def all_level_have_been_imported_into_database():
        return Level.objects.all().count() == 101

    @staticmethod
    @sync_to_async
    def load_to_cache():
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

    def __str__(self):
        return f"[Level {self.number} - {self.role_name}]"


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

    def get_countdown(self, current_time):
        seconds = round(self.reminder_date_epoch - current_time.timestamp())
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
