from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `autopost` ADD `postid` INT;
        ALTER TABLE `autopost` ADD `lastbiteindex` INT;
        ALTER TABLE `autopost` ADD `lastbiteid` INT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `autopost` DROP COLUMN `postid`;
        ALTER TABLE `autopost` DROP COLUMN `lastbiteindex`;
        ALTER TABLE `autopost` DROP COLUMN `lastbiteid`;"""
