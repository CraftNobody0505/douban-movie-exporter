# 豆瓣电影与读书记录导出

把自己的豆瓣电影和读书记录导出成 CSV，保存到本地。📚🎬

不需要安装第三方库，有 Python 3 就能运行。

## ✨ 这次升级了什么

- 新增豆瓣读书记录导出
- 电影支持：看过 / 想看 / 在看
- 读书支持：读过 / 想读 / 在读
- 支持评分、日期、短评、链接、封面等字段
- 支持登录 Cookie
- 自动放慢翻页速度，降低触发风控的概率

## 🎬 导出电影记录

运行：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID
```

默认导出「看过」。

导出「想看」：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status wish
```

导出「在看」：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status do
```

三类一起导出：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status all
```

## 📚 导出读书记录

运行：

```powershell
py douban_book_export.py --user YOUR_DOUBAN_ID
```

默认会把「读过 / 想读 / 在读」三类一起导出。

只导出「读过」：

```powershell
py douban_book_export.py --user YOUR_DOUBAN_ID --status collect
```

只导出「想读」：

```powershell
py douban_book_export.py --user YOUR_DOUBAN_ID --status wish
```

## 🔎 豆瓣 ID 在哪里

打开自己的豆瓣主页：

```text
https://www.douban.com/people/YOUR_DOUBAN_ID/
```

网址中间那段就是你的豆瓣 ID。

## 🍪 如果遇到 403

豆瓣有时会拒绝匿名脚本访问，这时需要浏览器 Cookie。

1. 登录豆瓣
2. 打开自己的电影或读书记录页面
3. 按 `F12` 打开开发者工具
4. 在 `Network` 里刷新页面
5. 点一个豆瓣请求，复制 Request Headers 里的 `Cookie`
6. 在脚本目录新建 `douban_cookie.txt`
7. 把 Cookie 粘进去，再运行脚本

⚠️ `douban_cookie.txt` 相当于登录凭据，不要发给别人，也不要上传到 GitHub。

## 🐢 慢一点更稳

如果记录很多，可以加大请求间隔：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --delay 10
```

```powershell
py douban_book_export.py --user YOUR_DOUBAN_ID --delay 15
```

## 📄 导出内容

电影 CSV 包含片名、评分、标记日期、短评、上映信息、豆瓣链接、subject id 和封面等。

读书 CSV 包含书名、评分、标记日期、短评、作者、出版社、出版日期、价格、标签、豆瓣链接、subject id 和封面等。

## ☕ 小提醒

这个项目适合备份自己的豆瓣记录。请控制请求频率，不要批量抓取他人数据，也不要商用。
