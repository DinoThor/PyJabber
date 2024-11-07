CREATE TABLE `roster`(
    `id` INTEGER,
    `jid` VARCHAR(255) NOT NULL,
    `rosterItem` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `pendingsub`(
    `jid_from` VARCHAR(255) NOT NULL,
    `jid_to` VARCHAR(255) NOT NULL,
    `item` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`jid_from`, `jid_to`)
);
CREATE TABLE `credentials`(
    `id` INTEGER,
    `jid` VARCHAR(255) NOT NULL UNIQUE,
    `hash_pwd` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `pubsub`(
    `node` VARCHAR(255),
    `name` VARCHAR(255),
    `type` VARCHAR(255),
    `subscribers` VARCHAR(255),
    `items` VARCHAR(255),
    PRIMARY KEY(`node`)
);
