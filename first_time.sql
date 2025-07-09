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
    payload   json      not null
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

create table if not exists giveaway
(
    id         serial,
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

alter table giveaway
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
    channel  numeric
);

alter table log
    owner to lumin;

create table if not exists giveaways
(
    id         serial,
    guild_id   numeric                                              not null,
    channel_id numeric                                              not null,
    message_id numeric                                              not null,
    author_id  numeric                                              not null,
    role_id    numeric,
    prize      text,
    winners    integer default 1                                    not null,
    ends_at    timestamp                                            not null,
    ended      boolean,
    won_by     numeric[],
    entered    numeric[]
);

alter table giveaways
    owner to lumin;
