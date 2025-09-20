create table if not exists afk
(
    id            serial,
    user_id       numeric not null,
    guild_id      numeric not null,
    message       text    not null,
    state         boolean not null,
    previous_nick text    not null
);

alter table afk
    owner to lumin;

create table if not exists cooldowns
(
    id       serial,
    guild_id numeric not null,
    command  text    not null,
    cooldown numeric
);

comment on column cooldowns.cooldown is 'In deciseconds (1 sec = 10)';

alter table cooldowns
    owner to lumin;

create table if not exists economy
(
    id       serial,
    guild_id numeric not null,
    user_id  numeric not null,
    cash     numeric default 0,
    bank     numeric default 0
);

alter table economy
    owner to lumin;

create table if not exists global_ban
(
    id          serial,
    user_id     numeric not null,
    reported_by numeric not null,
    reason      text    not null,
    accepted_by numeric not null
);

alter table global_ban
    owner to lumin;

create table if not exists global_ban_blacklist
(
    id      serial,
    user_id numeric not null
);

alter table global_ban_blacklist
    owner to lumin;

create table if not exists guilds
(
    id                    serial,
    guild_id              numeric not null,
    prefix                text    default '?!'::text,
    mention               boolean default true,
    embed_colour          numeric default 6656243,
    global_ban_state      boolean default true,
    global_ban_channel_id numeric
);

alter table guilds
    owner to lumin;

create table if not exists join_messages
(
    id         serial,
    guild_id   numeric not null,
    channel_id numeric not null,
    message    json
);

alter table join_messages
    owner to lumin;

create table if not exists leave_messages
(
    id         serial,
    guild_id   numeric not null,
    channel_id numeric not null,
    message    json
);

alter table leave_messages
    owner to lumin;

create table if not exists messages
(
    id       serial,
    guild_id numeric not null,
    payload  json
);

alter table messages
    owner to lumin;

create table if not exists shop
(
    id               serial,
    guild_id         numeric not null,
    creator_id       numeric not null,
    item_name        text    not null,
    item_description text    not null,
    item_price       numeric not null,
    role             numeric not null
);

alter table shop
    owner to lumin;

create table if not exists snapshots
(
    id        serial,
    guild_id  numeric   not null,
    name      text      not null,
    author_id numeric   not null,
    date      timestamp not null,
    code      text      not null,
    payload jsonb not null
);

alter table snapshots
    owner to lumin;

create table if not exists cases
(
    id           serial
        primary key,
    type         smallint,
    guild_id     numeric not null,
    case_id      numeric,
    user_id      numeric not null,
    moderator_id numeric not null,
    reason       text,
    expires      timestamp,
    message      text,
    created      timestamp default now()
);

alter table cases
    owner to lumin;

create table if not exists giveaways
(
    id         serial            not null,
    guild_id   numeric           not null,
    channel_id numeric           not null,
    message_id numeric           not null,
    author_id  numeric           not null,
    role_id    numeric,
    prize      text,
    winners    integer default 1 not null,
    ends_at    timestamp         not null,
    ended      boolean,
    won_by     numeric[]
);

alter table giveaways
    owner to lumin;

create table if not exists closed_beta
(
    guild_id numeric not null,
    added_by numeric
);

alter table closed_beta
    owner to lumin;

create table if not exists log
(
    id       serial,
    guild_id numeric              not null
        constraint log_pk
            unique,
    is_on    boolean default true not null,
    webhook  text,
    channel numeric,
    modules text[] default ARRAY ['on_automod_rule_create'::text, 'on_automod_rule_update'::text, 'on_automod_rule_delete'::text, 'on_automod_action'::text, 'on_guild_channel_delete'::text, 'on_guild_channel_create'::text, 'on_guild_channel_update'::text, 'on_guild_channel_pins_update'::text, 'on_guild_update'::text, 'on_guild_emojis_update'::text, 'on_guild_stickers_update'::text, 'on_invite_create'::text, 'on_invite_delete'::text, 'on_guild_integrations_update'::text, 'on_webhooks_update'::text, 'on_raw_integration_delete'::text, 'on_member_join'::text, 'on_member_remove'::text, 'on_member_update'::text, 'on_member_ban'::text, 'on_member_ban'::text, 'on_member_unban'::text, 'on_message_edit'::text, 'on_message_delete'::text, 'on_bulk_message_delete'::text, 'on_poll_vote_add'::text, 'on_poll_vote_remove'::text, 'on_reaction_add'::text, 'on_reaction_remove'::text, 'on_reaction_clear'::text, 'on_reaction_clear_emoji'::text, 'on_guild_role_create'::text, 'on_guild_role_delete'::text, 'on_scheduled_event_create'::text, 'on_scheduled_event_delete'::text, 'on_scheduled_event_update'::text, 'on_soundboard_sound_create'::text, 'on_soundboard_sound_delete'::text, 'on_soundboard_sound_update'::text, 'on_stage_instance_create'::text, 'on_stage_instance_delete'::text, 'on_stage_instance_update'::text, 'on_thread_create'::text, 'on_thread_join'::text, 'on_thread_update'::text, 'on_thread_remove'::text, 'on_thread_delete'::text, 'on_thread_member_join'::text, 'on_thread_member_remove'::text, 'on_voice_state_update'::text]
);

alter table log
    owner to lumin;
