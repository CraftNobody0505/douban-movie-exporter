# 豆瓣电影记录导出

把你的豆瓣电影「看过 / 想看 / 在看」记录导出成 CSV，放到本地慢慢整理。  
不需要安装第三方库，一个 Python 脚本就能跑。

## 能导出什么

📽️ 支持三类电影记录：

- `collect`：看过
- `wish`：想看
- `do`：在看

📝 CSV 里会包含：

- 片名
- 你的评分
- 标记日期
- 短评
- 上映日期
- 国家 / 地区
- 豆瓣链接
- 豆瓣 subject id
- 封面链接
- 列表页简介

## 怎么用

先准备 Python 3，然后运行：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID
```

`YOUR_DOUBAN_ID` 换成你的豆瓣 ID。

比如你的电影主页是：

```text
https://movie.douban.com/people/YOUR_DOUBAN_ID/
```

那 `YOUR_DOUBAN_ID` 就是中间那段。

## 导出不同状态

导出「看过」：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status collect
```

导出「想看」：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status wish
```

导出「在看」：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status do
```

三类都导出：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status all
```

## 如果遇到 403

豆瓣有时候不让匿名脚本访问，会返回 `403 Forbidden`。  
这时候需要用你浏览器里的 Cookie。

做法：

1. 登录豆瓣
2. 打开你的豆瓣电影记录页面
3. 按 `F12` 打开开发者工具
4. 在 `Network` 里刷新页面
5. 找一个 `movie.douban.com` 请求
6. 复制 Request Headers 里的 `Cookie`
7. 在脚本同目录新建 `douban_cookie.txt`
8. 把 Cookie 粘进去，再重新运行脚本

⚠️ 不要把 `douban_cookie.txt` 发给别人，也不要上传到 GitHub。  
仓库里的 `.gitignore` 已经默认忽略它。

## 慢一点更稳

默认每页会等几秒，别跑太猛。  
如果你的记录很多，可以把间隔调大：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --delay 10
```

## 中断了怎么办

豆瓣电影列表每页 15 条。  
如果跑到一半停了，可以用 `--start` 从某个位置继续。

比如从第 32 页继续：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --start 465
```

计算方式：

```text
start = (页码 - 1) × 15
```

## 小提醒

🍵 这个脚本适合备份自己的豆瓣电影记录。  
请控制请求频率，不要拿它批量抓别人数据，也不要商用。
