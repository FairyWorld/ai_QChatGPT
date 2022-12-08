from mirai import At, GroupMessage, MessageEvent, Mirai, Plain, StrangerMessage, WebSocketAdapter, FriendMessage, Image
import pkg.openai.session
from func_timeout import func_set_timeout, FunctionTimedOut
import datetime

help_text = """帮助信息：
!help - 显示帮助
!reset - 重置会话
!last - 切换到上一次的对话
!next - 切换到下一次的对话
!prompt - 显示当前对话所有内容
!list - 列出所有历史会话"""

inst = None

processing = []


class QQBotManager:
    timeout = 60
    retry = 3

    bot = None

    def __init__(self, mirai_http_api_config: dict, timeout: int = 60, retry: int = 3):

        self.timeout = timeout
        self.retry = retry

        bot = Mirai(
            qq=mirai_http_api_config['qq'],
            adapter=WebSocketAdapter(
                verify_key=mirai_http_api_config['verifyKey'],
                host=mirai_http_api_config['host'],
                port=mirai_http_api_config['port']
            )
        )

        @bot.on(FriendMessage)
        async def on_friend_message(event: FriendMessage):
            return await self.on_person_message(event)

        @bot.on(StrangerMessage)
        async def on_stranger_message(event: StrangerMessage):
            return await self.on_person_message(event)

        @bot.on(GroupMessage)
        async def on_group_message(event: GroupMessage):
            return await self.on_group_message(event)

        self.bot = bot

        global inst
        inst = self

    # 统一的消息处理函数
    @func_set_timeout(timeout)
    def process_message(self, launcher_type: str, launcher_id: int, text_message: str) -> str:
        reply = ''
        session_name = "{}_{}".format(launcher_type, launcher_id)

        if text_message.startswith('!') or text_message.startswith("！"):  # 指令
            cmd = text_message[1:].strip().split(' ')[0]

            params = text_message[1:].strip().split(' ')[1:]
            if cmd == 'help':
                reply = "[bot]" + help_text
            elif cmd == 'reset':
                pkg.openai.session.get_session(session_name).reset(explicit=True)
                reply = "[bot]会话已重置"
            elif cmd == 'last':
                result = pkg.openai.session.get_session(session_name).last_session()
                if result is None:
                    reply = "[bot]没有上一次的对话"
                else:
                    datetime_str = datetime.datetime.fromtimestamp(result.create_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    reply = "[bot]已切换到上一次的对话：\n创建时间:{}\n".format(datetime_str) + result.prompt[:min(100, len(result.prompt))] + \
                            ("..." if len(result.prompt) > 100 else "#END#")
            elif cmd == 'next':
                result = pkg.openai.session.get_session(session_name).next_session()
                if result is None:
                    reply = "[bot]没有下一次的对话"
                else:
                    datetime_str = datetime.datetime.fromtimestamp(result.create_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    reply = "[bot]已切换到下一次的对话：\n创建时间:{}\n".format(datetime_str) + result.prompt[:min(100, len(result.prompt))] + \
                            ("..." if len(result.prompt) > 100 else "#END#")
            elif cmd == 'prompt':
                reply = "[bot]当前对话所有内容：\n" + pkg.openai.session.get_session(session_name).prompt
            elif cmd == 'list':
                pkg.openai.session.get_session(session_name).persistence()
                page = 0

                if len(params) > 0:
                    try:
                        page = int(params[0])
                    except ValueError:
                        pass

                results = pkg.openai.session.get_session(session_name).list_history(page=page)
                if len(results) == 0:
                    reply = "[bot]第{}页没有历史会话".format(page)
                else:
                    reply = "[bot]历史会话 第{}页：\n".format(page)
                    current = -1
                    for i in range(len(results)):
                        # 时间(使用create_timestamp转换) 序号 部分内容
                        datetime_obj = datetime.datetime.fromtimestamp(results[i]['create_timestamp'])
                        reply += "#{} 创建:{} {}\n".format(i + page * 10, datetime_obj.strftime("%Y-%m-%d %H:%M:%S"),
                                                          results[i]['prompt'][:min(20, len(results[i]['prompt']))])
                        if results[i]['create_timestamp'] == pkg.openai.session.get_session(session_name).create_timestamp:
                            current = i + page * 10

                    reply += "以上信息倒序排列"
                    if current != -1:
                        reply += ",当前会话是 #{}\n".format(current)
                    else:
                        reply += ",当前处于全新会话"

        else:  # 消息
            session = pkg.openai.session.get_session(session_name)
            reply = "[GPT]" + session.append(text_message)

        return reply

    async def on_person_message(self, event: MessageEvent):
        if "person_{}".format(event.sender.id) in processing:
            return await self.bot.send(event, "err:正在处理中，请稍后再试")

        reply = ''

        if event.sender.id == self.bot.qq:
            pass
        else:
            if Image in event.message_chain:
                pass
            else:
                processing.append("person_{}".format(event.sender.id))

                # 超时则重试，重试超过次数则放弃
                failed = 0
                for i in range(self.retry):
                    try:
                        reply = self.process_message('person', event.sender.id, str(event.message_chain))
                        break
                    except FunctionTimedOut:
                        failed += 1
                        continue

                if failed == self.retry:
                    reply = "err:请求超时"

                processing.remove("person_{}".format(event.sender.id))

        if reply != '':
            return await self.bot.send(event, reply)

    async def on_group_message(self, event: GroupMessage):
        if "group_{}".format(event.group.id) in processing:
            return await self.bot.send(event, "err:正在处理中，请稍后再试")

        reply = ''

        if Image in event.message_chain:
            pass
        elif At(self.bot.qq) not in event.message_chain:
            pass
        else:
            event.message_chain.remove(At(self.bot.qq))

            processing.append("group_{}".format(event.sender.id))

            # 超时则重试，重试超过次数则放弃
            failed = 0
            for i in range(self.retry):
                try:
                    reply = self.process_message('group', event.group.id, str(event.message_chain).strip())
                    break
                except FunctionTimedOut:
                    failed += 1
                    continue

            if failed == self.retry:
                reply = "err:请求超时"

            processing.remove("group_{}".format(event.sender.id))

        if reply != '':
            return await self.bot.send(event, reply)


def get_inst() -> QQBotManager:
    global inst
    return inst