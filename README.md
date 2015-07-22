# DWeixin
Wechat development based on Django

### 介绍

微信公众平台开发 2.0 版本，优化了原先的一些功能，新增“事件外部处理”支持等。  
并且这是一个完整可运行的工程。  
详细请参阅我的博客：http://www.dannysite.com/blog/206/

### 包依赖

* Pythhon == 2.7.3+，暂时不支持 3.x 版本
* django == 1.6.x，该版本基于 1.6.5 开发
* MySQL-python == 1.2.3
* django-grappelli == 2.5.x，注意不能使用更高或更低版本
* lxml == 3.3.6
* beautifulsoup4 == 4.3.2
* redis == 2.9.1

### 常用配置项

以下常用的配置可在 settings 中加入或修改：

* WEIXIN_REDIS_HOST：Redis 服务器地址，默认为 localhost
* WEIXIN_REDIS_PORT：Redis 服务器端口，默认为 6379
* WEIXIN_REDIS_DB：Redis 数据库号，默认为 0
* WEIXIN_REDIS_PASSWORD：Redis 连接密码，默认为空

* HOST：当前域名

### 更新历史

###### 2.0.0
---
主要增加事件的“外部处理”功能，并分为同步和异步处理。主要借助于 Redis 作为中间缓存。  
另外，该版本加入了对多用户和几个新菜单事件的处理。

###### 2.1.0
---

* 增加对微信企业号的支持，所支持的功能与原平台内已经支持的功能一致
* 增加对账户重复的数据容错处理
* 优化微信用户授权机制（不再限制在平台对接前已关注当前公众号的微信用户与平台的交互）
* 修复消息加密的编码 BUG
* 修复关键字缓存初始化机制的 BUG
* 修复微信账户切换或配置更改时 access_token 未刷新的 BUG
* 其它 BUG 修复
