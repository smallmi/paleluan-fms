Paleluan FMS 运维管理系统(苍鸾)
=======================

[![Python Version](https://img.shields.io/badge/Python--3.6-paasing-green.svg)](https://img.shields.io/badge/Python--3.6-paasing-green.svg)
[![Django Version](https://img.shields.io/badge/Django--1.11.0-paasing-green.svg)](https://img.shields.io/badge/Django--1.11.0-paasing-green.svg)

项目作者：小瓶盖  QQ:1374409300

> PFMS现有功能: （QQ交流群：374506612）

- Dashboard
- 资产管理
- 发布管理
- 故障管理
- 权限管理
- 集成Xadmin



## 部署须知：
Python版本：3.6.x
Django版本：1.11.x

### 安装依赖

```
pip3 install -i https://pypi.douban.com/simple/  -r requirements.txt
git clone https://github.com/twz915/DjangoUeditor3.git
```

### 修改配置


MySQL配置修改settings.py:

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'fms',
        'USER': 'root',
        'PASSWORD': 'xxxx',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```
修改故障通知邮箱settings.py:

```
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = False
EMAIL_HOST = 'service.smallmi.com'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'admin@service.smallmi.com'
EMAIL_HOST_PASSWORD = 'xxx'
DEFAULT_FROM_EMAIL = 'smallmi <admin@service.smallmi.com>'

```

### 初始化数据
```
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata default_types
python manage.py loaddata default_user

```

### 登录

```
python manage.py runserver
http://127.0.0.1:8000
admin admin
```

主站：www.smallmi.com

项目演示：http://demo.smallmi.com
