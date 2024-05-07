CREATE TABLE `roster`(
    `jid` VARCHAR(255) NOT NULL,
    `rosterItem` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`jid`)
);
CREATE TABLE `credentials`(
    `jid` VARCHAR(255) NOT NULL,
    `hash_pwd` VARCHAR(255) NOT NULL,
    PRIMARY KEY(`jid`)
);