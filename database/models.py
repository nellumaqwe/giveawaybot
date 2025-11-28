from tortoise import Model, fields
from settings import main_bot

class BaseModel(Model):
    id = fields.IntField(pk=True)

    class Meta:
        abstract = True


class Giveaway(BaseModel):
    title = fields.CharField(max_length = 50)
    bot = fields.IntField(default = 0)
    winners_amount = fields.IntField(default = 0)
    required_refs_amount = fields.IntField(default = 0)
    end_type = fields.TextField(default = 'manual')
    end_date = fields.TextField(null = True)
    status = fields.TextField(default = 'new')
    sponsors = fields.TextField(default = '[]')
    participants = fields.TextField(default = '[]')
    participants_ended_task = fields.TextField(default = '[]')
    winners = fields.TextField(default = '[]')
    winner322 = fields.TextField(default = '')
    winners322_amount = fields.IntField(null = True)
    winners322_amount_tasks = fields.IntField(null = True)
    admin = fields.TextField(null = False)
    

    class Meta:
        table = "giveaways"

class Bots(BaseModel):
    token = fields.CharField(max_length = 50)
    username = fields.TextField(null = False)
    status = fields.TextField(default = "active")

    class Meta:
        table = "bots"


class Sponsors(BaseModel):
    invite_link = fields.TextField(null = False)
    chat_id = fields.BigIntField(null = False)
    title = fields.TextField(null = False)
    giveaway = fields.IntField(null = False)

    class Meta:
        table = "sponsors"


class Admin(BaseModel):
    admin_id = fields.BigIntField(null = True)
    username = fields.TextField(null = True)
    name = fields.TextField(null = True)
    status322 = fields.TextField(default = 'disabled')
    vip = fields.BooleanField(default = False)
    page = fields.IntField(default = 1)

    class Meta:
        table = "admins"


class Autopost(BaseModel):
    title = fields.TextField(null = False)
    admin = fields.BigIntField(null = False)
    chatmsgtext = fields.TextField(default = '')
    chatmsgbuttontext = fields.TextField(default = 'Перейти')
    buttonlink = fields.TextField(default = '')
    gachannel = fields.BigIntField(null = True)
    rassilkadelay = fields.IntField(default = 0)
    rassilkastatus = fields.TextField(default = 'off')
    postphoto = fields.TextField(default = '')
    postid = fields.IntField(null = True)
    lastbiteid = fields.IntField(null=True)
    lastbiteindex = fields.IntField(null = True)

    class Meta:
        table = "autopost"

class Gachannel(BaseModel):
    admin = fields.BigIntField(null = False)
    chatid = fields.BigIntField(null = False)
    name = fields.TextField(default = '')

    class Meta:
        table = "gachannel"


class Bites(BaseModel):
    admin = fields.BigIntField(null = False)
    text = fields.TextField(null = False)
    lastid = fields.IntField(default = 1)

    class Meta:
        table = "bites"


class Users(BaseModel):
    userid = fields.BigIntField(null = True)

    table = "users"