# reviewboard-hook
提供http服务用于提交diff到reviewboard

hook目录中的post-commit复制到svn repostory目录下的hooks中，修改下ip和端口。
将其他放置到任意目录，执行python manage.py runserver 0.0.0.0:8000启动hook http服务。
