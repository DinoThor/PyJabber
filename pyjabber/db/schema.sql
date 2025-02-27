CREATE TABLE `roster`(
    `id` INTEGER,
    `jid` VARCHAR(255) NOT NULL,
    `rosterItem` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `pendingsub`(
    `jid` VARCHAR(255) NOT NULL,
    `item` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`jid`, `item`)
);
CREATE TABLE `credentials`(
    `id` INTEGER,
    `jid` VARCHAR(255) NOT NULL UNIQUE,
    `hash_pwd` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `pubsub`(
    `node` VARCHAR(255),
    `owner` VARCHAR(255) NOT NULL,
    `name` VARCHAR(255),
    `type` VARCHAR(255),
    `maxitems` INTEGER,
    PRIMARY KEY(`node`)
);
CREATE TABLE `pubsubSubscribers`(
    `node` VARCHAR(255),
    `jid` VARCHAR(255),
    `subid` VARCHAR (255),
    `subscription` VARCHAR(255) NOT NULL,
    `affiliation` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`node`, `jid`, `subid`)
);
CREATE TABLE `pubsubItems`(
    `node` VARCHAR(255),
    `itemid` VARCHAR(255),
    `payload` VARCHAR (255),
    PRIMARY KEY(`node`, `itemid`)
);
