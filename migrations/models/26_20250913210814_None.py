from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `admins` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `admin_id` BIGINT,
    `username` LONGTEXT,
    `name` LONGTEXT,
    `status322` LONGTEXT NOT NULL,
    `vip` BOOL NOT NULL DEFAULT 0,
    `page` INT NOT NULL DEFAULT 1
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `autopost` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `giveaway` INT NOT NULL,
    `chatmsgtext` LONGTEXT NOT NULL,
    `chatmsgbuttontext` LONGTEXT NOT NULL,
    `buttonlink` LONGTEXT NOT NULL,
    `gachannel` BIGINT,
    `rassilkadelay` INT NOT NULL DEFAULT 0,
    `rassilkatext` LONGTEXT NOT NULL,
    `rassilkastatus` LONGTEXT NOT NULL,
    `postphoto` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `bots` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `token` VARCHAR(50) NOT NULL,
    `username` LONGTEXT NOT NULL,
    `status` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `gachannel` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `admin` BIGINT NOT NULL,
    `chatid` BIGINT NOT NULL,
    `name` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `giveaways` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(50) NOT NULL,
    `bot` INT NOT NULL DEFAULT 0,
    `winners_amount` INT NOT NULL DEFAULT 0,
    `required_refs_amount` INT NOT NULL DEFAULT 0,
    `end_type` LONGTEXT NOT NULL,
    `end_date` LONGTEXT,
    `status` LONGTEXT NOT NULL,
    `sponsors` LONGTEXT NOT NULL,
    `participants` LONGTEXT NOT NULL,
    `participants_ended_task` LONGTEXT NOT NULL,
    `winners` LONGTEXT NOT NULL,
    `winner322` LONGTEXT NOT NULL,
    `admin` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sponsors` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `invite_link` LONGTEXT NOT NULL,
    `chat_id` BIGINT NOT NULL,
    `title` LONGTEXT NOT NULL,
    `giveaway` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
