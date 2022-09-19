import discord
import random
import os
from discord import app_commands
from discord.ext import commands  # Bot Commands Frameworkのインポート
from typing import Literal
from .modules.readjson import ReadJson
from logging import getLogger
from .modules.coyote import Coyote
from .modules.ohgiri import Ohgiri, OhrgiriStart
from os.path import join, dirname
from .modules import settings
from .modules.savefile import SaveFile
from .modules.members import Members
# from .modules import gamebuttons #あとで消す
from .modules import games
from logging import getLogger
LOG = getLogger('assistantbot')

POLL_CHAR = ['🇦','🇧','🇨','🇩','🇪','🇫','🇬','🇭','🇮','🇯','🇰','🇱','🇲','🇳','🇴','🇵','🇶','🇷','🇸','🇹']

# コグとして用いるクラスを定義。
class GameCog(commands.Cog, name='ゲーム用'):
    """
    ゲーム機能のカテゴリ。
    """
    guilds = []
    MAX_TIME = 10
    DEFAULT_TIME = 2
    SHOW_ME = '自分のみ'
    SHOW_ALL = '全員に見せる'

    # GameCogクラスのコンストラクタ。Botを受取り、インスタンス変数として保持。
    def __init__(self, bot):
        self.bot = bot
        self.coyoteGames = {}
        self.ohgiriGames = {}
        self.ohgiriStart = None
        self.wordWolfJson = None
        self.ngWordGameJson = None
        self.savefile = SaveFile()
        self.ww_members = {}
        self.ng_members = {}
        self.cy_members = {}
        self.oh_members = {}

    # cogが準備できたら読み込みする
    @commands.Cog.listener()
    async def on_ready(self):
        self.ohgiriGames['default'] = Ohgiri()
        await self.ohgiriGames['default'].on_ready()
        await self.wordWolf_setting()
        await self.ngWordGame_setting()

    async def wordWolf_setting(self):
        wordWolf_filepath = join(dirname(__file__), 'modules' + os.sep + 'files' + os.sep + 'temp' + os.sep + 'wordwolf.json')
        if not os.path.exists(wordWolf_filepath) or \
            (not settings.USE_IF_AVAILABLE_FILE and settings.WORDWOLF_JSON_URL ):
            wordWolf_filepath = await self.json_setting(settings.WORDWOLF_JSON_URL, 'wordwolf.json')
        # ファイルを読み込み、ワードウルフ用のデータを作成
        read_json = ReadJson()
        read_json.readJson(wordWolf_filepath)
        self.wordWolfJson = read_json

    async def ngWordGame_setting(self):
        ngWordGame_filepath = join(dirname(__file__), 'modules' + os.sep + 'files' + os.sep + 'temp' + os.sep + 'ngword_game.json')
        if not os.path.exists(ngWordGame_filepath) or \
            (not settings.USE_IF_AVAILABLE_FILE and settings.NGWORD_GAME_JSON_URL ):
            ngWordGame_filepath = await self.json_setting(settings.NGWORD_GAME_JSON_URL, 'ngword_game.json')
        # ファイルを読み込み、NGワードゲーム用のデータを作成
        read_json = ReadJson()
        read_json.readJson(ngWordGame_filepath)
        self.ngWordGameJson = read_json

    async def json_setting(self, json_url=None, file_name='no_name.json'):
        json_path = join(dirname(__file__), 'modules' + os.sep + 'files' + os.sep + 'temp' + os.sep + file_name)
        # URLが設定されている場合はそちらを使用
        if json_url:
            file_path = await self.savefile.download_file(json_url,  json_path)
            LOG.info(f'JSONのURLが登録されているため、JSONを保存しました。\n{file_path}')
            return file_path

    # ワードウルフ機能
    @app_commands.command(
        name='start-word-wolf',
        description='ワードウルフ機能(少数派のワードを与えられた人を当てるゲーム)')
    @app_commands.describe(
        answer_minutes='投票開始までの時間（3などの正数。単位は「分」）を与えることができます。デフォルトは2分です')
    async def wordWolf(self, interaction: discord.Interaction, answer_minutes: app_commands.Range[int, 1, 10] = 2):
        """
        コマンド実行者が参加しているボイスチャンネルでワードウルフ始めます（BOTからDMが来ますがびっくりしないでください）
        引数(answer_minutes)として投票開始までの時間（3などの正数。単位は「分」）を与えることができます。デフォルトは2分です。
        3人増えるごとにワードウルフは増加します(3−5人→ワードウルフは1人、6−8人→ワードウルフは2人)
        """
        if answer_minutes is None:
            answer_minutes = self.DEFAULT_TIME

        # もう入力できない想定
        if answer_minutes > self.MAX_TIME:
            msg = f'ワードウルフはそんなに長い時間するものではないです(現在、{answer_minutes}分を指定しています。{self.MAX_TIME}分以内にして下さい)'
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # このコマンドが実行された時点でギルドごとのメンバーが設定されていなければ、作っておく
        if not interaction.guild_id in self.ww_members:
            self.ww_members[interaction.guild_id] = Members()
        self.ww_members[interaction.guild_id].set_minutes(answer_minutes)

        msg =   'ワードウルフを始めます(3人以上必要です)！  この中に、**ワードウルフ**が紛れ込んでいます(本人も知りません！/3人増えるごとに1人がワードウルフです)。\n'\
                'DMでお題が配られますが、**ワードウルフだけは別のお題**が配られます(お題は2種類あります)。会話の中で不審な言動を察知し、みごとに'\
                '投票でワードウルフを当てることができたら、市民の勝ち。**間違えて「市民をワードウルフ」だと示してしまった場合、ワードウルフの勝ち**です！！\n'\
                '参加する場合、以下のボタンを押してください。'
        # await interaction.channel.send(msg)
        view = games.WordwolfStart(self.ww_members, self.wordWolfJson, msg)
        await interaction.response.send_message(msg, view=view)

    #     # コヨーテ
    #     coyote_components=[gamebuttons.cy_join_action_row,gamebuttons.cy_leave_action_row]
    #     if interaction.guild_id in self.coyoteGames:
    #         if self.coyoteGames[interaction.guild_id].set_deck_flg:
    #             coyote_components.append(gamebuttons.cyw_start_action_row)
    #         else:
    #             coyote_components.append(gamebuttons.cy_start_action_row)
    #         coyote_components.append(gamebuttons.cy_purge_action_row)

    #     if interaction.custom_id == gamebuttons.CUSTOM_ID_JOIN_COYOTE:
    #         if interaction.guild_id in self.cy_members:
    #             self.cy_members[interaction.guild_id].add_member(interaction.user)
    #         else:
    #             self.coyoteGames[interaction.guild_id] = Coyote()
    #             self.cy_members[interaction.guild_id] = Members()
    #             self.cy_members[interaction.guild_id].add_member(interaction.user)
    #         LOG.debug(f'追加:{interaction.user.display_name}')
    #         await interaction.edit_origin(content=f'{interaction.user.display_name}が参加しました!(参加人数:{self.cy_members[interaction.guild_id].len})', components=coyote_components)
    #     if interaction.custom_id == gamebuttons.CUSTOM_ID_LEAVE_COYOTE:
    #         if interaction.guild_id in self.cy_members:
    #             self.cy_members[interaction.guild_id].remove_member(interaction.user)
    #         else:
    #             self.coyoteGames[interaction.guild_id] = Coyote()
    #             self.cy_members[interaction.guild_id] = Members()
    #         LOG.debug(f'削除:{interaction.user.display_name}')
    #         await interaction.edit_origin(content=f'{interaction.user.display_name}が離脱しました!(参加人数:{self.cy_members[interaction.guild_id].len})', components=coyote_components)
    #     if interaction.custom_id == gamebuttons.CUSTOM_ID_PURGE_COYOTE:
    #         self.coyoteGames[interaction.guild_id] = Coyote()
    #         self.cy_members[interaction.guild_id] = Members()
    #         LOG.debug(f'参加者クリア:{interaction.user.display_name}')
    #         await interaction.edit_origin(content=f'参加者がクリアされました(参加人数:{self.cy_members[interaction.guild_id].len})', components=coyote_components)
    #     if interaction.custom_id == gamebuttons.CUSTOM_ID_START_COYOTE:
    #         if interaction.guild_id not in self.cy_members:
    #             msg = f'ゲームが始まっていません。`/start-coyote-game`でゲームを開始してください。'
    #             self.cy_members[interaction.guild_id] = Members()
    #             self.coyoteGames[interaction.guild_id] = Coyote()
    #             await interaction.edit_origin(content=msg, components=coyote_components)
    #             return
    #         if self.cy_members[interaction.guild_id].len < 2:
    #             msg = f'コヨーテを楽しむには2人以上のメンバーが必要です(現在、{self.cy_members[interaction.guild_id].len}人しかいません)'
    #             await interaction.edit_origin(content=msg, components=coyote_components)

    #             return
    #         await self.startCoyote(ctx)
    #         if self.coyoteGames[interaction.guild_id].start_description == 'Normal':
    #             """
    #             説明が程よいバージョン
    #             - コヨーテのルールが分かる程度に省略しています。
    #             """
    #             await self.coyoteLittleMessage(ctx)
    #         elif self.coyoteGames[interaction.guild_id].start_description == 'All':
    #             """
    #             説明が多いバージョン
    #             - 初心者はこちらのコマンドを実行してください。
    #             - コヨーテのルールが分かるように書いてありますが、一旦説明を見ながらゲームしてみると良いと思います。
    #             """
    #             await self.coyoteAllMessage(ctx)
    #         elif self.coyoteGames[interaction.guild_id].start_description == 'Nothing':
    #             """
    #             コヨーテを始めるコマンド（説明なし）
    #             - 上級者向けの機能です。ルールを説明されずとも把握している場合にのみ推奨します。
    #             """
    #             msg = self.coyoteGames[interaction.guild_id].create_description(True)
    #             await interaction.response.send_message(msg)
    #         await self.dealAndMessage(ctx)
    #     if interaction.custom_id == gamebuttons.CUSTOM_ID_START_COYOTE_SET_DECK:
    #         if interaction.guild_id not in self.cy_members:
    #             msg = f'ゲームが始まっていません。`/start-coyote-game-set-deck`でゲームを開始してください。'
    #             self.cy_members[interaction.guild_id] = Members()
    #             self.coyoteGames[interaction.guild_id] = Coyote()
    #             await interaction.edit_origin(content=msg, components=coyote_components)
    #             return
    #         if self.cy_members[interaction.guild_id].len < 2:
    #             msg = f'コヨーテを楽しむには2人以上のメンバーが必要です(現在、{self.cy_members[interaction.guild_id].len}人しかいません)'
    #             await interaction.edit_origin(content=msg, components=coyote_components)
    #             return
    #         self.coyoteGames[interaction.guild_id].set(self.cy_members[interaction.guild_id].get_members())
    #         self.coyoteGames[interaction.guild_id].shuffle()
    #         msg = self.coyoteGames[interaction.guild_id].create_description(True)
    #         await interaction.response.send_message(msg)
    #         await self.dealAndMessage(ctx)
    #     if interaction.custom_id == gamebuttons.CUSTOM_ID_DEAL_COYOTE:
    #         if await self.coyoteStartCheckNG(ctx):
    #             return
    #         await self.dealAndMessage(ctx)
    #     if interaction.custom_id == gamebuttons.CUSTOM_ID_DESC_CARD_COYOTE:
    #         if interaction.guild_id not in self.cy_members:
    #             self.coyoteGames[interaction.guild_id] = Coyote()
    #             self.cy_members[interaction.guild_id] = Members()
    #         msg = self.coyoteGames[interaction.guild_id].create_description_card()
    #         await interaction.edit_origin(content=msg)
    #     if interaction.custom_id == gamebuttons.CUSTOM_ID_DESC_TURN_COYOTE:
    #         if await self.coyoteStartCheckNG(interaction: discord.Interaction, True):
    #             return
    #         msg = self.coyoteGames[interaction.guild_id].create_description()
    #         await interaction.edit_origin(content=msg)

    # NGワードゲーム機能
    @app_commands.command(
        name='start-ng-word-game',
        description='NGワードゲーム機能(禁止された言葉を喋ってはいけないゲーム)')
    @app_commands.describe(
        answer_minutes='投票開始までの時間（3などの正数。単位は「分」）を与えることができます。デフォルトは2分です')
    async def ngWordGame(self, interaction: discord.Interaction, answer_minutes: app_commands.Range[int, 1, 10] = 2):
        """
        コマンド実行者が参加しているボイスチャンネルでNGワードゲームを始めます（BOTからDMが来ますがびっくりしないでください）
        引数(answer_minutes)として終了までの時間（3などの正数。単位は「分」）を与えることができます。デフォルトは2分です。
        """
        if answer_minutes is None:
            answer_minutes = self.DEFAULT_TIME

        # このコマンドが実行された時点でギルドごとのメンバーが設定されていなければ、作っておく
        if not interaction.guild_id in self.ng_members:
            self.ng_members[interaction.guild_id] = Members()
        self.ng_members[interaction.guild_id].set_minutes(answer_minutes)

        # もう入力できない想定
        if answer_minutes > self.MAX_TIME:
            msg = f'NGワードゲームはそんなに長い時間するものではないです(現在、{answer_minutes}分を指定しています。{self.MAX_TIME}分以内にして下さい)'
            await interaction.response.send_message(msg, ephemeral=True)
            return

        msg =   'NGワードゲームを始めます(2人以上必要です)！  これからDMでそれぞれのNGワードを配ります！(**自分のNGワードのみ分かりません**)\n'\
                '配られた後に**雑談し、誰かがNGワードを口走ったら、「ドーン！！！」と指摘**してください。すぐさまNGワードが妥当か話し合いください(カッコがある場合は、どちらもNGワードです)。\n'\
                '妥当な場合、NGワード発言者はお休みです。残った人で続けます。**最後のひとりになったら勝利**です！！\n'\
                '参加する場合、以下のボタンを押してください。'
        # await interaction.channel.send(msg)
        view = games.NgWordGameStart(self.ng_members, self.ngWordGameJson, msg)
        await interaction.response.send_message(msg, view=view)

    # @app_commands.command(
    #     name='start-coyote-game',
    #     description='コヨーテ機能(場にある数値の合計を推測しつつ遊ぶゲーム)')
    # @app_commands.describe(
    #     descriptionLiteral='コヨーテを始める際の説明')
    # async def start(self, interaction: discord.Interaction, descriptionLiteral: Literal['普通', '詳しく', '無し']):
    #     description = Coyote.DESCRPTION_NORMAL
    #     if descriptionLiteral  == '詳しく':
    #         description = Coyote.DESCRPTION_ALL
    #     elif descriptionLiteral == '無し':
    #         description = Coyote.DESCRPTION_NOTHING
    #     msg = 'コヨーテを始めます(2人以上必要です)！\n参加する場合、以下のボタンを押してください。'
    #     await interaction.response.send_message(msg)
    #     await interaction.response.send_message('ボタン', components=[gamebuttons.cy_join_action_row])
    #     self.coyoteGames[interaction.guild_id] = Coyote()
    #     self.cy_members[interaction.guild_id] = Members()
    #     self.coyoteGames[interaction.guild_id].set_deck_flg = False
    #     self.coyoteGames[interaction.guild_id].start_description = description

    # @app_commands.command(
    # name='start-coyote-game-set-deck',
    # # guild_ids=guilds,
    # description='【上級者向け】デッキを指定しコヨーテを開始 :例：`/start-coyote-game-set-deck 20,0(Night),-5,*2(Chief), Max->0(Fox),?(Cave)`',
    # options=[
    #     manage_commands.create_option(name='deck',
    #                                 description='デッキを「,」(コンマ)で区切って指定(例：`/start-coyote-game-set-deck 20,0,0(Night),-5,*2(Chief), Max->0(Fox),?(Cave)`)',
    #                                 option_type=3,
    #                                 required=True)
    # ])
    # async def setDeckAndStart(self, interaction: discord.Interaction, deck=None):
    #     """
    #     デッキを指定してコヨーテを始めるコマンド（説明なし）
    #     - 上級者向けの機能です。ルールを説明されずとも把握している場合にのみ推奨します。
    #     - デッキを「,」(コンマ)で区切って指定します。二重引用符などは不要です。
    #     例：`/coyoteGame setDeckAndStart 20, 15, 15, 1, 1, 1, 1, 0, 0, 0, 0(Night), -5, -5, -10, *2(Chief), Max->0(Fox), ?(Cave), ?(Cave)`
    #     """
    #     msg = 'デッキを指定してコヨーテを始めます(2人以上必要です)！\n参加する場合、以下のボタンを押してください。'
    #     await interaction.response.send_message(msg)
    #     await interaction.response.send_message('ボタン', components=[gamebuttons.cy_join_action_row])
    #     self.coyoteGames[interaction.guild_id] = Coyote()
    #     self.cy_members[interaction.guild_id] = Members()
    #     self.coyoteGames[interaction.guild_id].setDeck(deck)

    # @app_commands.command(
    # name='coyote-game-coyote',
    # # guild_ids=guilds,
    # description='コヨーテ！(前プレイヤーの数字がコヨーテの合計数を超えたと思った場合のコマンド)',
    # options=[
    #     manage_commands.create_option(name='target_id',
    #                                 description='プレイヤーのID（@マークを打つと入力しやすい）',
    #                                 option_type=3,
    #                                 required=True)
    #     , manage_commands.create_option(name='number',
    #                                 description='前プレイヤーの宣言した数',
    #                                 option_type=3,
    #                                 required=True)
    # ])
    # async def coyote(self, interaction: discord.Interaction, target_id=None, number=0):
    #     """
    #     コヨーテ中に実行できる行動。「コヨーテ！」を行う
    #     - 「コヨーテ！」は前プレイヤーの宣言を疑う行動
    #     - 「前プレイヤーの宣言した数」が「実際にこの場にいるコヨーテの数よりも**大きい（オーバーした）**」と思う場合に実行してください
    #     引数は2つあり、どちらも必須です
    #     - 1.プレイヤーのID（@マークを打つと入力しやすい）
    #     - 2.前プレイヤーの宣言した数
    #     """
    #     if number.isdecimal():
    #         number = int(number)
    #     else:
    #         number = 0

    #     if target_id is None:
    #         msg = '「コヨーテする相手」(@で指定)と「コヨーテを言われた人の数字」を指定してください。例：`coyote-game-coyote @you 99`'
    #         await interaction.response.send_message(msg, ephemeral=True)
    #         return
    #     if number <= 0:
    #         msg = '「コヨーテを言われた人の数字」は「1以上の整数」(0もダメです)を指定してください。例：`coyote-game-coyote @you 99`'
    #         await interaction.response.send_message(msg, ephemeral=True)
    #         return
    #     if await self.coyoteStartCheckNG(ctx):
    #         return
    #     # コヨーテ！した相手のメンバー情報を取得。取得できない場合はエラーを返す
    #     target_id = re.sub(r'[<@!>]', '', target_id)
    #     if target_id.isdecimal():
    #         target_id = int(target_id)
    #         you = interaction.guild.get_member(target_id)
    #     else:
    #         # IDから取得を試みる
    #         keys = [k for k, v in self.coyoteGames[interaction.guild_id].members.items() if v.id == str(target_id).upper()]
    #         if len(keys) == 0:
    #             msg = '「コヨーテする相手」(@で指定するか、IDで指定(aなど))と「コヨーテを言われた人の数字」を指定してください。例：`coyote-game-coyote @you 99`'
    #             await interaction.response.send_message(msg)
    #             return
    #         else:
    #             you = keys.pop()
    #     if you not in self.coyoteGames[interaction.guild_id].members:
    #         msg = 'ゲームに存在する相手を選び、「コヨーテ！」してください(ゲームしている相手にはいません)。'
    #         await interaction.response.send_message(msg)
    #         return

    #     self.coyoteGames[interaction.guild_id].coyote(interaction.user, you, number)
    #     await interaction.response.send_message(self.coyoteGames[interaction.guild_id].description)
    #     await interaction.response.send_message('ボタン', components=[gamebuttons.cy_deal_action_row, gamebuttons.cy_desc_card_action_row, gamebuttons.cy_desc_turn_action_row])

    # @app_commands.command(
    # name='coyote-game-deal',
    # # guild_ids=guilds,
    # description='ディール(次のターンを始める)')
    # async def deal(self, ctx):
    #     """
    #     コヨーテ中に実行できる行動。カードを引いて、プレイヤーに配ります
    #     """
    #     if await self.coyoteStartCheckNG(ctx):
    #         return
    #     await self.dealAndMessage(ctx)

    # @app_commands.command(
    # name='coyote-game-description',
    # # guild_ids=guilds,
    # description='状況説明orカード能力の説明します',
    # options=[
    #     manage_commands.create_option(name='description_target',
    #                                         description='状況説明or状況説明(ネタバレ)orカード能力説明',
    #                                         option_type=3,
    #                                         required=True,
    #                                         choices=[
    #                                             manage_commands.create_choice(
    #                                             name='状況説明(ターン数,HP,山札の数,捨て札の数,捨て札)',
    #                                             value='Description-Normal'),
    #                                             manage_commands.create_choice(
    #                                             name='【ネタバレ】状況説明(全て/場のカードも分かる)',
    #                                             value='Description-All'),
    #                                             manage_commands.create_choice(
    #                                             name='カードの説明',
    #                                             value='Description-Cards')
    #                                         ])
    #     , manage_commands.create_option(name='reply_is_hidden',
    #                                         description='Botの実行結果を全員に見せるどうか(他の人に説明を見せたい場合、全員に見せる方がオススメです))',
    #                                         option_type=3,
    #                                         required=False,
    #                                         choices=[
    #                                             manage_commands.create_choice(
    #                                             name='自分のみ',
    #                                             value='True'),
    #                                             manage_commands.create_choice(
    #                                             name='全員に見せる',
    #                                             value='False')
    #                                         ])
    # ])
    # async def description(self, interaction: discord.Interaction, description_target, reply_is_hidden:str = None):
    #     hidden = True if reply_is_hidden == 'True' else False
    #     if description_target == 'Description-Cards':
    #         """カードの能力を説明します。"""
    #         msg = self.coyoteGames[interaction.guild_id].create_description_card()
    #         await interaction.response.send_message(msg, hidden=hidden)
    #         return
    #     else:
    #         if await self.coyoteStartCheckNG(interaction: discord.Interaction, True):
    #             return
    #         if description_target == 'Description-Normal':
    #             """
    #             状況を説明します。
    #             - ターン数、生き残っている人の数、それぞれのHP
    #             - 山札の数、捨て札の数、捨て札の中身
    #             """
    #             msg = self.coyoteGames[interaction.guild_id].create_description()
    #         elif description_target == 'Description-All':
    #             """
    #             状況を全て説明します（場のカードもわかります）。
    #             - ターン数、生き残っている人の数、それぞれのHP
    #             - 山札の数、山札の中身、捨て札の数、捨て札の中身、場のカード
    #             """
    #             msg = self.coyoteGames[interaction.guild_id].create_description(True)
    #         await    # @commands.command(aliases=['dice','dices','r'], description='ダイスを振る(さいころを転がす)')

    @app_commands.command(name='roll', description='ダイスを振る(さいころを転がす)')
    @app_commands.describe(dice_and_num='「/roll 1d6」のように、左側にダイスの数、右側にダイスの種類(最大値)を指定')
    @app_commands.describe(reply_is_hidden='Botの実行結果を全員に見せるどうか(デフォルトは全員に見せる)')
    async def roll(self, interaction: discord.Interaction, dice_and_num: str, reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        """
        ダイスを振る(さいころを転がす)コマンド
        - `/roll 1d6`のように、左側にダイスの数、右側にダイスの種類(最大値)を指定してください
        """
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        default_error_msg = '`/roll 1d6`のように指定してください。'
        LOG.debug(f'dice_and_num:{dice_and_num}')
        if dice_and_num is None:
            await interaction.response.send_message(default_error_msg, ephemeral=True)
            return
        dice_and_num = str(dice_and_num).lower()
        if 'd' not in dice_and_num:
            msg = 'dが必ず必要です。'
            await interaction.response.send_message(msg + default_error_msg, ephemeral=True)
            return
        list = str(dice_and_num).split('d')
        if len(list) != 2:
            await interaction.response.send_message(default_error_msg, ephemeral=True)
            return
        elif len(list) == 2:
            msg = ''
            sum = 0
            # ダイスの数、ダイスの最大値についてのチェックと数値化
            if list[0].isdecimal():
                dice_num = int(list[0])
            else:
                msg = 'dの左側が数字ではありません。'
                await interaction.response.send_message(msg + default_error_msg, ephemeral=True)
                return
            if list[1].isdecimal():
                max_num = int(list[1])
            else:
                msg = 'dの右側が数字ではありません。'
                await interaction.response.send_message(msg + default_error_msg, ephemeral=True)
                return
            if max_num < 1 or dice_num < 1:
                msg = 'dの左右は1以上である必要があります。'
                await interaction.response.send_message(msg + default_error_msg, ephemeral=True)
                return
            for i in range(dice_num):
                value = random.randint(1, max_num)
                msg += f' {value}'
                sum += value
            else:
                if dice_num > 1:
                    msg += f' → {sum}'
                await interaction.response.send_message(msg, ephemeral=hidden)

    # async def startCoyote(self, ctx):
    #     self.coyoteGames[interaction.guild_id].setInit(self.cy_members[interaction.guild_id].get_members())
    #     self.coyoteGames[interaction.guild_id].shuffle()

    # async def dealAndMessage(self, ctx):
    #     self.coyoteGames[interaction.guild_id].deal()
    #     start_msg = await interaction.response.send_message(f'カードを配りました。DMをご確認ください。{self.coyoteGames[interaction.guild_id].description}')
    #     dm_msg_all = ''
    #     # 全員分のメッセージを作成
    #     for player in self.coyoteGames[interaction.guild_id].members:
    #         dm_msg_all += f'{player.display_name}さん: {self.coyoteGames[interaction.guild_id].members[player].card}\n'
    #     # DM用メッセージを作成(送付する相手の名前が記載された行を削除)
    #     for player in self.coyoteGames[interaction.guild_id].members:
    #         dm = await player.create_dm()
    #         rpl_msg_del = f'{player.display_name}さん:.+\n'
    #         dm_msg = re.sub(rpl_msg_del, '', dm_msg_all)
    #         await dm.send(f'{player.mention}さん 他の人のコヨーテカードはこちらです！\n{dm_msg}開始メッセージへのリンク: {self.rewrite_link_at_me(start_msg.jump_url, interaction.guild_id)}')
    #     self.coyoteGames[interaction.guild_id].description = ''

    # async def coyoteAllMessage(self, ctx):
    #     msg1 = 'コヨーテ：ゲーム目的\n**自分以外のプレイヤーのカード(DMに送られる)を見て、少なくとも何匹のコヨーテがこの場にいるかを推理します。**\n'\
    #         'もしも宣言した数だけ居なかったら......コヨーテに命を奪われてしまいます！ インディアン、嘘つかない。コヨーテだって、嘘が大キライなのです。\n'\
    #         'ライフは一人3ポイントあります。3回殺されたらゲームから退場します。\n'\
    #         'コヨーテの鳴き声（想像してね）が上手いプレイヤーから始めます。'
    #     await interaction.response.send_message(msg1)

    #     msg2 = '最初のプレイヤーはDMに送られる他の人のカードを見て、この場に「少なくとも」何匹のコヨーテがいるか(DMを見て数字を加算し)推理し、コヨーテの数を宣言します。\n'\
    #         '★宣言する数に上限はありませんが、**1以上の整数である必要**があります（つまり、0や負数はダメです）\n'\
    #         'ゲームは時計回りに進行(ボイスチャンネルを下に進むこと)します。\n'\
    #         '次のプレイヤーは次のふたつのうち、「どちらか」の行動をとってください。\n'\
    #         '1: 数字を上げる → 前プレイヤーの宣言した数が実際にこの場にいるコヨーテの数**以下（オーバー）していない**と思う場合、**前プレイヤーより大きな数**を宣言します。\n'\
    #         '2: 「コヨーテ！」→ 前プレイヤーの宣言を疑います。つまり、前プレイヤーの宣言した数が実際にこの場にいるコヨーテの数よりも**大きい（オーバーした）**と思う場合、**「コヨーテ！」**と宣言します\n'\
    #         '2の場合、例：`coyote-game-coyote @you 99`のように(`@you`はidでもOK)**Discordに書き込んで**ください！（Botが結果を判定します！）\n'\
    #         '**誰かが「コヨーテ！」と宣言するまで**、時計回りで順々に交代しながら宣言する数字を上げていきます\n'
    #     await interaction.response.send_message(msg2)

    #     msg3 = '「コヨーテ！」と宣言された場合、直前のプレイヤーが宣言した数が当たっていたかどうか判定します。\n'\
    #         '★前述の通り、Botが計算します（例：`coyote-game-coyote @you 99`のように書き込んでくださいね）\n'\
    #         'まず基本カードを集計したあと、特殊カード分を計算します。\n'\
    #         '「コヨーテ！」を**宣言された数がコヨーテの合計数をオーバー**していた場合、**「コヨーテ！」を宣言した人**の勝ち（数値を宣言した人の負け）\n'\
    #         '「コヨーテ！」を**宣言された数がコヨーテの合計数以下**の場合、**数値を宣言**した人の勝ち（「コヨーテ！」を宣言した人の負け）\n'\
    #         '負けたプレイヤーはダメージを受けます（ライフが減ります）。\n'\
    #         '使ったカードを捨て札にして、次の回を始めます（**今回負けた人から開始**します）。\n'\
    #         '次の回を始めるには、`/coyote-game-deal `をDiscordに書き込んでください。\n'\
    #         '負けたプレイヤーがその回を最後に**ゲームから脱落した場合、その回の勝者から**次の回を始めます。\n'\
    #         'ライフが0になったプレイヤーはゲームから脱落します。最後まで生き残ったプレイヤーが勝利です。\n'\
    #         'なお、コヨーテは絶賛販売中です(1,800円くらい)。気に入った方はぜひ買って遊んでみてください（このBotは許可を得て作成したものではありません）。販売:合同会社ニューゲームズオーダー, 作者:Spartaco Albertarelli, 画:TANSANFABRIK\n'\
    #         'サイト: <http://www.newgamesorder.jp/games/coyote>'
    #     await interaction.response.send_message(msg3)

    #     msg4 = self.coyoteGames[interaction.guild_id].create_description(True)
    #     await interaction.response.send_message(msg4)
    #     card_msg = self.coyoteGames[interaction.guild_id].create_description_card()
    #     await interaction.response.send_message(card_msg)

    # async def coyoteLittleMessage(self, ctx):
    #     msg = 'コヨーテ：ゲーム目的\n**自分以外のプレイヤーのカード(DMに送られる)を見て、少なくとも何匹のコヨーテがこの場にいるかを推理します。**\n'\
    #         'もしも宣言した数だけ居なかったら......コヨーテに命を奪われてしまいます！ インディアン、嘘つかない。コヨーテだって、嘘が大キライなのです。\n'\
    #         'ライフは一人3ポイントあります。3回殺されたらゲームから退場します。\n'\
    #         '最初のプレイヤー:「少なくとも」何匹のコヨーテがいるか推理し、コヨーテの数を宣言(**1以上の整数**)します。\n'\
    #         'ゲームは時計回りに進行(ボイスチャンネルを下に進むこと)\n'\
    #         '次のプレイヤー：は次のふたつのうち、「どちらか」の行動をとってください。\n'\
    #         '1: 数字を上げる → 前プレイヤーの宣言した数が実際にこの場にいるコヨーテの数**以下（オーバー）していない**と思う場合、**前プレイヤーより大きな数**を宣言します。\n'\
    #         '2: 「コヨーテ！」→ 前プレイヤーの宣言を疑います。つまり、前プレイヤーの宣言した数が実際にこの場にいるコヨーテの数よりも**大きい（オーバーした）**と思う場合、**「コヨーテ！」**と宣言します\n'\
    #         '2の場合、例：`coyote-game-coyote @you 99`のように(`@you`はidでもOK)**Discordに書き込んで**ください！（Botが結果を判定します！）\n'\
    #         '**誰かが「コヨーテ！」と宣言するまで**、時計回り(ボイスチャンネルを下に進む)で順々に交代しながら宣言する**数字を上げて**いきます\n'\
    #         '次の回を始めるには、`/coyote-game-deal `をDiscordに書き込んでください（**今回負けた人から開始**します）。\n'\
    #         '負けたプレイヤーがその回を最後に**ゲームから脱落した場合、その回の勝者から**次の回を始めます。\n'\
    #         'ライフが0になったプレイヤーはゲームから脱落します。最後まで生き残ったプレイヤーが勝利です。\n'\
    #         'なお、コヨーテは絶賛販売中です(1,800円くらい)。気に入った方はぜひ買って遊んでみてください（このBotは許可を得て作成したものではありません）。販売:合同会社ニューゲームズオーダー, 作者:Spartaco Albertarelli, 画:TANSANFABRIK\n'\
    #         'サイト: <http://www.newgamesorder.jp/games/coyote>'
    #     await interaction.response.send_message(msg)
    #     msg2 = self.coyoteGames[interaction.guild_id].create_description(True)
    #     await interaction.response.send_message(msg2)
    #     card_msg = self.coyoteGames[interaction.guild_id].create_description_card()
    #     await interaction.response.send_message(card_msg)

    # async def coyoteStartCheckNG(self, interaction: discord.Interaction, desc=False):
    #     if interaction.guild_id not in self.coyoteGames or self.coyoteGames[interaction.guild_id] is None or (len(self.coyoteGames[interaction.guild_id].members) <= 1 and not desc):
    #         msg = 'コヨーテを始めてから実行できます。コヨーテを始めたい場合は、`/start-coyote-game`を入力してください。'
    #         await interaction.response.send_message(msg, ephemeral=True)
    #         return True
    #     # 終わった後に説明が見たい場合は許す
    #     elif len(self.coyoteGames[interaction.guild_id].members) == 1 and desc:
    #         return False
    #     else:
    #         return False

    @app_commands.command(
        name='start-ohgiri-game',
        description='大喜利を開始(親が好みのネタをカードから選んで優勝するゲーム)')
    @app_commands.describe(
        win_point='勝利扱いとするポイント(デフォルトは3ポイント)')
    async def start_ohgiriGame(self, interaction: discord.Interaction, win_point: app_commands.Range[int, 1, 20] = 3):
        """
        大喜利を開始
        - win_point: 勝利扱いとするポイント(デフォルトは3ポイント)
        """
        self.ohgiriGames[interaction.guild_id] = Ohgiri()
        self.ohgiriGames[interaction.guild_id].file_path = self.ohgiriGames['default'].file_path
        self.ohgiriGames[interaction.guild_id].win_point = win_point
        self.oh_members[interaction.guild_id] = Members()

        msg =   '大喜利を始めます(2人以上必要です)！\n参加する場合、以下のボタンを押してください。'
        self.ohgiriStart = OhrgiriStart(self.oh_members, self.ohgiriGames, msg)
        await interaction.response.send_message(msg, view=self.ohgiriStart)

    @app_commands.command(
        name='ohgiri-game-answer',
        description='【子】回答者がお題に提出する回答を設定')
    @app_commands.describe(
        card_id='回答として設定する値(数字で指定)')
    @app_commands.describe(
        second_card_id='回答として設定する値(数字で指定)')
    async def answer(self, interaction: discord.Interaction, card_id: str=None, second_card_id: str=None):
        """
        回答者が回答として提出するカードを設定
        - ans_number: 回答として設定する値(数字で指定)
        例:`/ohgiri-game-answer 1`
        """
        # 始まっているかのチェック
        if interaction.guild_id not in self.ohgiriGames or len(self.ohgiriGames[interaction.guild_id].members) == 0 or self.ohgiriGames[interaction.guild_id].game_over:
            await interaction.response.send_message('ゲームが起動していません！', ephemeral=True)
        # コマンド実行者のチェック(親は拒否)
        elif interaction.user == self.ohgiriGames[interaction.guild_id].house:
            await interaction.response.send_message('親は回答を提出できません！', ephemeral=True)
        # 引数が設定されているかチェック
        elif card_id is None:
            await interaction.response.send_message('引数`card_id`を指定してください！', ephemeral=True)
        # 参加者かチェック
        elif self.ohgiriGames[interaction.guild_id].members.get(interaction.user) is None:
            await interaction.response.send_message(f'{interaction.user.display_name}は、参加者ではありません！', ephemeral=True)
        # コマンド実行者が所持しているかチェック
        elif card_id not in self.ohgiriGames[interaction.guild_id].members[interaction.user].cards:
            await interaction.response.send_message(f'{card_id}は{interaction.user.display_name}の所持しているカードではありません！', ephemeral=True)
        elif self.ohgiriGames[interaction.guild_id].required_ans_num == 1 and second_card_id is not None:
            await interaction.response.send_message('お題で2つ設定するように指定がないので、回答は1つにしてください！', ephemeral=True)
        elif self.ohgiriGames[interaction.guild_id].required_ans_num == 2 and second_card_id is None:
            await interaction.response.send_message('2つめの引数`second_card_id`が設定されていません！(もう一つ数字を設定してください)', ephemeral=True)
        elif self.ohgiriGames[interaction.guild_id].required_ans_num == 2 and second_card_id not in self.ohgiriGames[interaction.guild_id].members[interaction.user].cards:
            await interaction.response.send_message(f'{second_card_id}は{interaction.user.display_name}の所持しているカードではありません！', ephemeral=True)
        else:
            LOG.debug('回答を受け取ったよ！')
            # 既に回答したメンバーから再度回答を受けた場合、入れ替えた旨お知らせする
            if self.ohgiriGames[interaction.guild_id].members[interaction.user].answered:
                await interaction.response.send_message(f'{interaction.user.mention} 既に回答を受け取っていたため、そちらのカードと入れ替えますね！', ephemeral=True)
            # カードの受領処理
            self.ohgiriGames[interaction.guild_id].receive_card(card_id, interaction.user, second_card_id)
            # 回答者が出そろった場合、場に出す(親は提出できないので引く)
            if (len(self.ohgiriGames[interaction.guild_id].members) - 1)  == len(self.ohgiriGames[interaction.guild_id].field):
                self.ohgiriGames[interaction.guild_id].show_answer()
                LOG.info('回答者が出揃ったので、場に展開！')
                msg = self.ohgiriGames[interaction.guild_id].description + f'\n{self.ohgiriGames[interaction.guild_id].house.mention} 回答を読み上げたのち、好きな回答を`/ohgiri-game-choice <数字>`で選択してください！'
                await interaction.response.send_message(msg)
            else:
                await interaction.response.send_message('回答ありがとうございます', ephemeral=True)

    @app_commands.command(
        name='ohgiri-game-choice',
        description='【親】回答者がお題に提出する回答を設定')
    @app_commands.describe(
        ans_index='気に入ったカードの回答番号を設定する値(数字で指定)')
    async def choice(self, interaction: discord.Interaction, ans_index: str=None):
        """
        親が気に入ったカードを選択する
        - ans_index: 気に入ったカードの回答番号を設定する値(数字で指定)
        例:`/ohgiri-game-choice 1`
        """
        # 始まっているかのチェック
        if interaction.guild_id not in self.ohgiriGames or len(self.ohgiriGames[interaction.guild_id].members) == 0 or self.ohgiriGames[interaction.guild_id].game_over:
            await interaction.response.send_message('ゲームが起動していません！', ephemeral=True)
        # コマンド実行者のチェック(親以外は拒否)
        elif interaction.user != self.ohgiriGames[interaction.guild_id].house:
            await interaction.response.send_message('親以外が秀逸な回答を選択することはできません！', ephemeral=True)
        elif ans_index is None or not ans_index.isdecimal():
            await interaction.response.send_message('`ans_index`が選択されていません！', ephemeral=True)
        # 回答が出揃っているかチェック
        elif (len(self.ohgiriGames[interaction.guild_id].members) - 1)  > len(self.ohgiriGames[interaction.guild_id].field):
            await interaction.response.send_message(f'回答が出揃っていません。あと{len(self.ohgiriGames[interaction.guild_id].members) - len(self.ohgiriGames[interaction.guild_id].field) -1}人提出が必要です。', ephemeral=True)

        else:
            # 場にある数かどうかのチェック
            if int(ans_index) > len(self.ohgiriGames[interaction.guild_id].members) - 1:
                await interaction.response.send_message(f'{ans_index}は場に出ている最大の選択数({len(self.ohgiriGames[interaction.guild_id].members) - 1})を超えています！', ephemeral=True)
                return

            # 結果を表示
            self.ohgiriGames[interaction.guild_id].choose_answer(ans_index)
            await interaction.response.send_message(self.ohgiriGames[interaction.guild_id].description)

            # ゲームが終了していない場合、次のターンを開始
            if not self.ohgiriGames[interaction.guild_id].game_over:
                await self.ohgiriStart.dealAndNextGame(interaction)

    @app_commands.command(
        name='ohgiri-game-description',
        description='現在の状況を説明')
    async def description_ohgiriGame(self, interaction: discord.Interaction):
        """現在の状況を説明します"""
        # 始まっているかのチェック
        if interaction.guild_id not in self.ohgiriGames or len(self.ohgiriGames[interaction.guild_id].members) == 0:
            await interaction.response.send_message('ゲームが起動していません！', ephemeral=True)
            return
        self.ohgiriGames[interaction.guild_id].show_info()
        await interaction.response.send_message(self.ohgiriGames[interaction.guild_id].description)

    @app_commands.command(
        name='ohgiri-game-discard_hand',
        description='ポイントを1点減点し、手札をすべて捨て、山札からカードを引く(いい回答カードがない時に使用ください)')
    async def discard_hand(self, interaction: discord.Interaction):
        """
        ポイントを1点減点し、手札をすべて捨て、山札からカードを引く（いい回答カードがない時に使用ください）
        """
        # 始まっているかのチェック
        if interaction.guild_id not in self.ohgiriGames or len(self.ohgiriGames[interaction.guild_id].members) == 0 or self.ohgiriGames[interaction.guild_id].game_over:
            await interaction.response.send_message('ゲームが起動していません！', ephemeral=True)
            return
        self.ohgiriGames[interaction.guild_id].discard_hand(interaction.user)
        await interaction.response.send_message(self.ohgiriGames[interaction.guild_id].description, ephemeral=True)
        await self.send_ans_dm(interaction, interaction.user)

    # poll機能
    @app_commands.command(
        name='simple-poll',
        description='簡易的な投票機能です(/で分割されます。「/がない」場合と「/がある」場合で動作が変わります)')
    @app_commands.describe(
        poll_message='タイトル/回答1/回答2/...のスタイルで入力ください(タイトルのみの場合、Yes/Noで投票されます)')
    async def poll(self, interaction: discord.Interaction, poll_message: str):
        """
        このコマンドを実行すると、リアクションを利用し簡易的な投票ができます。
        ＊1人1票にはできません。リアクションの制限で20を超える設問は不可能です。
        """
        usage = '/simple-pollの使い方\n複数選択（1〜20まで）: \n `/simple-poll 今日のランチは？/お好み焼き/カレーライス`\n Yes/No: \n`/poll 明日は晴れる？`'
        args_all = poll_message.split('/')
        msg = f'🗳 **{args_all[0]}**'
        await interaction.response.send_message('投票開始')
        channel = interaction.channel
        if len(args_all)  == 1:
            message = await channel.send(msg)
            await message.add_reaction('⭕')
            await message.add_reaction('❌')
        elif len(args_all) > 21:
            await interaction.response.send_message(f'複数選択の場合、引数は1〜20にしてください。（{len(args_all)-1}個与えられています。）')
        else:
            args = args_all[1:]
            embed = discord.Embed()
            for  emoji, arg in zip(POLL_CHAR, args):
                embed.add_field(name=emoji, value=arg) # inline=False
            message = await channel.send(msg, embed=embed)

            for  emoji, arg in zip(POLL_CHAR, args):
                await message.add_reaction(emoji)

    # @commands.Cog.listener()
    # async def on_slash_command_error(self, interaction: discord.Interaction, ex):
    #     '''
    #     slash_commandでエラーが発生した場合の動く処理
    #     '''
    #     try:
    #         raise ex
    #     except discord.ext.commands.PrivateMessageOnly:
    #         await interaction.response.send_message(f'エラーが発生しました(DM(ダイレクトメッセージ)でのみ実行できます)', hidden = True)
    #     except discord.ext.commands.NoPrivateMessage:
    #         await interaction.response.send_message(f'エラーが発生しました(ギルドでのみ実行できます(DMやグループチャットでは実行できません))', hidden = True)
    #     except discord.ext.commands.NotOwner:
    #         await interaction.response.send_message(f'エラーが発生しました(Botのオーナーのみ実行できます)', hidden = True)
    #     except discord.ext.commands.MissingPermissions:
    #         if ex.missing_perms[0] == 'administrator':
    #             await interaction.response.send_message(f'エラーが発生しました(ギルドの管理者のみ実行できます)', hidden = True)
    #     except:
    #         await interaction.response.send_message(f'エラーが発生しました({ex})', hidden = True)

async def setup(bot):
    await bot.add_cog(GameCog(bot)) # GameCogにBotを渡してインスタンス化し、Botにコグとして登録する