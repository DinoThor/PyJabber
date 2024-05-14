CREATE TABLE `roster`(
    `id` INTEGER,
    `jid` VARCHAR(255) NOT NULL,
    `rosterItem` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `credentials`(
    `jid` VARCHAR(255) NOT NULL,
    `hash_pwd` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`jid`)
);