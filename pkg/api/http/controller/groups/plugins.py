from __future__ import annotations


import traceback

import quart

from .....core import app, taskmgr
from .. import group


@group.group_class('plugins', '/api/v1/plugins')
class PluginsRouterGroup(group.RouterGroup):

    async def initialize(self) -> None:
        @self.route('', methods=['GET'], auth_type=group.AuthType.USER_TOKEN)
        async def _() -> str:
            plugins = self.ap.plugin_mgr.plugins()

            plugins_data = [plugin.model_dump() for plugin in plugins]

            return self.success(data={
                'plugins': plugins_data
            })
        
        @self.route('/<author>/<plugin_name>/toggle', methods=['PUT'], auth_type=group.AuthType.USER_TOKEN)
        async def _(author: str, plugin_name: str) -> str:
            data = await quart.request.json
            target_enabled = data.get('target_enabled')
            await self.ap.plugin_mgr.update_plugin_switch(plugin_name, target_enabled)
            return self.success()
        
        @self.route('/<author>/<plugin_name>/update', methods=['POST'], auth_type=group.AuthType.USER_TOKEN)
        async def _(author: str, plugin_name: str) -> str:
            ctx = taskmgr.TaskContext.new()
            wrapper = self.ap.task_mgr.create_user_task(
                self.ap.plugin_mgr.update_plugin(plugin_name, task_context=ctx),
                kind="plugin-operation",
                name=f"plugin-update-{plugin_name}",
                label=f"更新插件 {plugin_name}",
                context=ctx
            )
            return self.success(data={
                'task_id': wrapper.id
            })
        
        @self.route('/<author>/<plugin_name>', methods=['DELETE'], auth_type=group.AuthType.USER_TOKEN)
        async def _(author: str, plugin_name: str) -> str:
            ctx = taskmgr.TaskContext.new()
            wrapper = self.ap.task_mgr.create_user_task(
                self.ap.plugin_mgr.uninstall_plugin(plugin_name, task_context=ctx),
                kind="plugin-operation",
                name=f'plugin-remove-{plugin_name}',
                label=f'删除插件 {plugin_name}',
                context=ctx
            )

            return self.success(data={
                'task_id': wrapper.id
            })

        @self.route('/reorder', methods=['PUT'], auth_type=group.AuthType.USER_TOKEN)
        async def _() -> str:
            data = await quart.request.json
            await self.ap.plugin_mgr.reorder_plugins(data.get('plugins'))
            return self.success()
        
        @self.route('/install/github', methods=['POST'], auth_type=group.AuthType.USER_TOKEN)
        async def _() -> str:
            data = await quart.request.json
            
            ctx = taskmgr.TaskContext.new()
            short_source_str = data['source'][-8:]
            wrapper = self.ap.task_mgr.create_user_task(
                self.ap.plugin_mgr.install_plugin(data['source'], task_context=ctx),
                kind="plugin-operation",
                name=f'plugin-install-github',
                label=f'安装插件 ...{short_source_str}',
                context=ctx
            )

            return self.success(data={
                'task_id': wrapper.id
            })
