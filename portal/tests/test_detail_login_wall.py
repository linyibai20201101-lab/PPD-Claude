"""Login-wall detection for tender-product detail fetch."""

from tender_product_analysis.detail_fetcher import _body_looks_like_login_wall


def test_login_wall_detected():
    text = (
        "欢迎来到剑鱼标讯\n微信扫码登录\n验证码登录 密码登录\n"
        "免费查询招标采购信息，对接项目联系人\n获取验证码\n"
    )
    assert _body_looks_like_login_wall(text) is True


def test_real_article_not_login_wall():
    text = "项目名称：工业相机采购\n预算金额：120万元\n" + ("技术参数说明 " * 20)
    assert _body_looks_like_login_wall(text) is False
