支持中国小牛电动车连接。修改了代码中的连接服务器，app-api-fk.niu.com改为app-api.niu.com，account-fk.niu.com改为account.niu.com

# Niu E-scooter Home Assistant integration

This is a custom component for Home Assistant to integrate your Niu Scooter.

Now this integration is _asynchronous_ and it is easy installable via config flow.

## Changes:
* Now it will generate automatically a Niu device so all the sensors and the camera will grouped
![auto device](images/niu_integration_device.png)
* If you select the Last track sensor automatically it will create a camera integration, with the rendered image of your last track.
![last track camera](images/niu_integration_camera.png)

With the thanks to pikka97 !!!

## Version 2.2.0 - AI-Enhanced Modernization
This version includes a comprehensive refactor performed by AI assistance to eliminate UI lag and improve reliability:

### Major Improvements:
- **Async Architecture**: Replaced synchronous `requests` with asynchronous `aiohttp` for non-blocking I/O
- **DataUpdateCoordinator**: Implemented centralized, throttled data updates to prevent UI freezes
- **Defensive Programming**: Added robust error handling with `.get()` methods to avoid crashes on missing data
- **SSL Compatibility**: Temporary workaround for SSL certificate verification issues (`verify_ssl=False`)
- **Modern Codebase**: Full migration to async/await patterns compatible with Home Assistant's event loop

### Technical Details:
- **API Client**: Complete rewrite of `api.py` using async methods
- **Configuration Flow**: Updated `config_flow.py` to use async authentication
- **Sensor Updates**: All sensors now use `CoordinatorEntity` for consistent data access
- **Performance**: 60-second update interval with efficient batch API calls

*Note: This refactor was performed with AI assistance to modernize the codebase and eliminate performance bottlenecks.*

## Setup
1. In Home Assistant's settings under "device and services" click on the "Add integration" button.
2. Search for "Niu Scooters" and click on it.
3. Insert your Niu app companion's credentials and select which sensors do you want.
![config flow](images/config_flow_niu_integration.png)
4. Enjoy your new Niu integration :-)

## Known bugs

some people had problems with this version please take the latest 1.o  versions
See https://github.com/marcelwestrahome/home-assistant-niu-component repository
