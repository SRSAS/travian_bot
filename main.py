from utils import *
import selenium_manager as SM


@log_execution_time
def main():
    selenium_manager = SM.SeleniumManager()
    international_5_farming_menu = Menu(title=f"{SM.INTERNATIONAL_5}: farming", options=[Option(
        name="Select undefended oases", command=as_command(selenium_manager.select_undefended_oases_farms,
                                                           server=SM.INTERNATIONAL_5))])

    international_5_menu = Menu(title=f"{SM.INTERNATIONAL_5}", options=[Option(name="farming",
                                                                               command=international_5_farming_menu)]
                                )
    main_menu = Menu(title="Server selection", options=[Option(name=international_5_menu.title,
                                                               command=international_5_menu)],
                     on_close=[as_command(selenium_manager.close_driver, server=SM.INTERNATIONAL_5)])

    main_menu()

    logger.info("Waiting for all threads to finish to shutdown executor.")
    executor.shutdown()
    logger.info("Executor has shutdown.")

    return


if __name__ == "__main__":
    main()
