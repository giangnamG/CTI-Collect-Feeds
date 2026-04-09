# Semantic Signals Reference

Use this file only as optional reasoning support.
It is not a scoring model and must not replace Codex judgment.

## Chinese-Language Reading Rules

Treat titles as Chinese-first, even when they contain English fragments such as OTP, CVV, U盾, KYC, admin, panel, or bot.
Account for shorthand, slang, euphemisms, mixed scripts, and marketplace phrasing.
Infer from meaning and criminal workflow, not from one literal token.

## Strong Cybercrime Signals

Examples:

- 钓鱼页, 仿站, 登录页, 验证码拦截, OTP, 过盾, 短信转发
- 料子, 社工库, 开户料, 四件套, 身份证料, 人脸料, CVV, cookie, session
- 后台, 面板, 木马, 免杀, 远控, stealer, bot, 后门, 打包, 代维后台
- 洗钱, 跑分, 代收代付, 卡农, U商, 出入金, 通道, 盘口
- 假券商, 带单诈骗, 交易所杀猪盘, 投资盘, 无法提现, 证券带单群
- 税务仿站, 政务伪站, 公安/社保/海关/财政系统入口仿冒, 政府账号料
- 买, 卖, 出售, 收, 换, 代找, 中介, 担保, 接单, 供料, 黑页, 打站, 入侵, 爆破, 拿站

## Sector Hints

Examples:

- Banking: 银行, 网银, 手机银行, 银行卡, 信用卡, U盾, OTP, 转账, 开户, 对公, SWIFT
- Securities: 证券, 券商, 股票, 港股, 美股, 交易席位, 投顾, 带单, 开户, 打新
- Financial: 支付, 钱包, 代收代付, KYC, 出入金, 支付通道, 商户, 金融账户, fintech
- Government: 税务, 海关, 公安, 社保, 政务, 财政, 公积金, 政府门户, 电子政务

## Common Reject Patterns

Examples:

- 普通财经新闻, 宏观评论, 行业资讯, 政策解读
- 黑客新闻, 漏洞播报, 被攻击通报, 抓捕报道, 事件复盘, 舆情搬运
- 正常投资交流群, 证券教学, 技术分析, 财经直播
- 官方公告, 银行通知, 政务办事提醒, 普通招聘信息
- 只提到行业但没有诈骗、窃取、冒充、入侵、洗钱或非法变现含义的标题
- 只是描述新闻事件, 没有买卖, 交换, 中介撮合, 提供服务, 或直接实施攻击含义的标题

When uncertain, prefer a defensible reject.
