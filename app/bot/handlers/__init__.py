"""
Инициализация обработчиков для LeadBot.

Регистрирует все обработчики команд и callback'ов.
"""

from telegram.ext import Application, MessageHandler, filters

from .start import start_handler
from .lead_magnet import (
    get_gift_command,
    gift_button_callback,
    subscribe_channel_callback,
    check_subscription_callback
)
from .warmup import (
    warmup_offer_callback,
    warmup_info_callback,
    warmup_stop_callback,
    stop_followup_callback
)
from .tripwire import (
    payment_card_callback,
    payment_spb_callback,
    payment_help_callback
)
# Новая простая админ-панель для LeadBot
from .admin_simple import (
    admin_handler,
    admin_stats_callback,
    admin_users_callback,
    admin_lead_magnets_callback,
    admin_products_callback,
    admin_warmup_callback,
    admin_back_callback,
    edit_magnet_callback,
    delete_magnet_callback,
    confirm_delete_magnet_callback,
    edit_magnet_name_callback,
    edit_magnet_url_callback,
    edit_magnet_desc_callback,
    reset_all_lead_magnets_callback,
    admin_mailings_callback,
    create_mailing_callback,
    send_mailing_callback,
    resend_mailing_callback,
    edit_mailing_callback,
    delete_mailing_callback,
    confirm_delete_mailing_callback,
    view_scenario_callback,
    add_scenario_callback,
    edit_scenario_callback,
    delete_scenario_callback,
    confirm_delete_scenario_callback,
    edit_scenario_name_callback,
    edit_scenario_desc_callback,
    list_scenario_msgs_callback,
    add_scenario_msg_callback,
    msg_type_callback,
    edit_product_callback,
    delete_product_callback,
    confirm_delete_product_callback,
    edit_product_name_callback,
    edit_product_desc_callback,
    edit_product_price_callback,
    edit_product_url_callback,
    edit_product_offer_callback,
    add_product_callback,
    product_type_callback,
    admin_admins_callback,
    add_admin_callback,
    remove_admin_select_callback,
)
from .admin_manage import (
    toggle_magnet_callback,
    add_lead_magnet_callback,
    edit_warmup_callback,
    admin_text_handler,
    text_input_handler,
    file_handler,
    file_input_handler
)


def register_handlers(application: Application) -> None:
    """
    Регистрация всех обработчиков в приложении.
    
    Args:
        application: Экземпляр Application для регистрации обработчиков
    """
    # Команды
    application.add_handler(start_handler)
    application.add_handler(get_gift_command)
    application.add_handler(admin_handler)
    
    # Callback обработчики
    application.add_handler(gift_button_callback)
    application.add_handler(subscribe_channel_callback)
    application.add_handler(check_subscription_callback)
    application.add_handler(warmup_offer_callback)
    application.add_handler(warmup_info_callback)
    application.add_handler(warmup_stop_callback)
    application.add_handler(stop_followup_callback)
    application.add_handler(payment_card_callback)
    application.add_handler(payment_spb_callback)
    application.add_handler(payment_help_callback)
    
    # Админ callback handlers
    application.add_handler(admin_stats_callback)
    application.add_handler(admin_users_callback)
    application.add_handler(admin_lead_magnets_callback)
    application.add_handler(admin_products_callback)
    application.add_handler(admin_warmup_callback)
    application.add_handler(admin_back_callback)
    
    # Админ управление
    application.add_handler(toggle_magnet_callback)
    application.add_handler(add_lead_magnet_callback)
    application.add_handler(edit_warmup_callback)
    # Более специфичные паттерны лид-магнитов ПЕРЕД общими
    application.add_handler(confirm_delete_magnet_callback)
    application.add_handler(edit_magnet_name_callback)
    application.add_handler(edit_magnet_url_callback)
    application.add_handler(edit_magnet_desc_callback)
    application.add_handler(reset_all_lead_magnets_callback)
    application.add_handler(edit_magnet_callback)
    application.add_handler(delete_magnet_callback)
    # Рассылки
    application.add_handler(admin_mailings_callback)
    application.add_handler(create_mailing_callback)
    # Более специфичные паттерны рассылок ПЕРЕД общими
    application.add_handler(confirm_delete_mailing_callback)
    application.add_handler(resend_mailing_callback)
    application.add_handler(send_mailing_callback)
    application.add_handler(edit_mailing_callback)
    application.add_handler(delete_mailing_callback)
    application.add_handler(view_scenario_callback)
    application.add_handler(add_scenario_callback)
    # Более специфичные паттерны сценариев ПЕРЕД общими
    application.add_handler(confirm_delete_scenario_callback)
    application.add_handler(edit_scenario_name_callback)
    application.add_handler(edit_scenario_desc_callback)
    application.add_handler(list_scenario_msgs_callback)
    application.add_handler(add_scenario_msg_callback)
    application.add_handler(msg_type_callback)
    application.add_handler(edit_scenario_callback)
    application.add_handler(delete_scenario_callback)
    # Более специфичные паттерны продуктов ПЕРЕД общими
    application.add_handler(confirm_delete_product_callback)
    application.add_handler(edit_product_name_callback)
    application.add_handler(edit_product_desc_callback)
    application.add_handler(edit_product_price_callback)
    application.add_handler(edit_product_url_callback)
    application.add_handler(edit_product_offer_callback)
    application.add_handler(add_product_callback)
    application.add_handler(product_type_callback)
    application.add_handler(edit_product_callback)
    application.add_handler(delete_product_callback)
    # Админы
    application.add_handler(admin_admins_callback)
    application.add_handler(add_admin_callback)
    application.add_handler(remove_admin_select_callback)
    application.add_handler(admin_text_handler)  # Должен быть последним!
    
    # Обработчики файлов и текста для админ-панели
    application.add_handler(file_handler)  # Обработчик файлов
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input_handler))


__all__ = [
    "register_handlers",
    "start_handler",
    "get_gift_command",
    "gift_button_callback",
    "subscribe_channel_callback",
    "check_subscription_callback",
    "warmup_offer_callback",
    "warmup_info_callback",
    "warmup_stop_callback",
    "stop_followup_callback",
    "payment_card_callback",
    "payment_spb_callback",
    "payment_help_callback",
    "admin_command_handler",
    "admin_callback_handler"
]
