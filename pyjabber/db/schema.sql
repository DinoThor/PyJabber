CREATE TABLE `roster`(
    `id` INTEGER,
    `jid` VARCHAR(255) NOT NULL,
    `rosterItem` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `credentials`(
    `id` INTEGER,
    `jid` VARCHAR(255) NOT NULL UNIQUE,
    `hash_pwd` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`id`)
);