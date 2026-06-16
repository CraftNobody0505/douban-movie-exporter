# Douban Movie Exporter

一个简单的豆瓣电影记录导出脚本，可以把「看过 / 想看 / 在看」列表页导出为 CSV。

这个脚本只抓取豆瓣电影列表页，不进入每个电影详情页，尽量降低请求量和触发风控的概率。

## 功能

- 导出 `collect`：看过
- 导出 `wish`：想看
- 导出 `do`：在看
- 支持一次导出三类记录
- 支持登录 Cookie
- 支持从指定 `start` 位置续跑
- 输出 UTF-8 with BOM CSV，Excel 可以直接打开

## 字段

CSV 包含以下字段：

| 字段 | 含义 |
| --- | --- |
| `status` | 豆瓣状态：`collect` / `wish` / `do` |
| `status_label` | 中文状态 |
| `title` | 片名 |
| `rating` | 个人评分，1-5 星 |
| `rating_date` | 标记日期 |
| `comment` | 短评 |
| `release_date` | 上映日期，能从简介解析时填写 |
| `country` | 上映地区，能从简介解析时填写 |
| `intro` | 豆瓣列表页简介 |
| `link` | 豆瓣电影链接 |
| `subject_id` | 豆瓣 subject id |
| `cover` | 封面链接 |

## 使用

需要 Python 3，不依赖第三方包。

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID
```

导出想看：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status wish
```

导出看过、想看、在看三类：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --status all
```

指定输出目录：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --output-dir D:\exports
```

## Cookie

如果匿名访问返回 `403 Forbidden`，或豆瓣提示登录/安全验证，可以在脚本同目录创建：

```text
douban_cookie.txt
```

然后登录豆瓣，打开电影记录页面，按 F12 打开开发者工具，在 Network 里复制 `movie.douban.com` 请求的 `Cookie` 请求头值，粘贴到 `douban_cookie.txt`。

也可以直接通过参数传入：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --cookie "YOUR_COOKIE"
```

不要把 `douban_cookie.txt` 上传到 GitHub。仓库里的 `.gitignore` 已经默认忽略它。

## 续跑

豆瓣电影列表每页 15 条。如果中途停在第 32 页，可以从 `start=465` 继续：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --start 465
```

## 降低风控

默认每页等待 6 秒，并额外加入少量随机延迟。你也可以手动调大：

```powershell
py douban_movie_export.py --user YOUR_DOUBAN_ID --delay 10
```

建议：

- 不要频繁重复全量导出
- 不要同时跑多个脚本
- 不要抓详情页，列表页字段已经足够做归档

## 说明

本项目仅用于导出自己的豆瓣电影记录。请遵守豆瓣的服务条款，控制请求频率，不要用于批量抓取他人数据或商业用途。
