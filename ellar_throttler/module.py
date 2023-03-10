import typing as t

from ellar.common import Module
from ellar.core import IExecutionContext
from ellar.core.modules import DynamicModule, IModuleConfigure, ModuleBase
from ellar.di import ProviderConfig

from ellar_throttler.interfaces import IThrottlerStorage
from ellar_throttler.throttler_module_options import ThrottlerModuleOptions
from ellar_throttler.throttler_service import ThrottlerStorageService


@Module()
class ThrottlerModule(ModuleBase, IModuleConfigure):
    @classmethod
    def module_configure(
        cls,
        ttl: int,
        limit: int,
        storage: t.Union[t.Type, t.Any] = None,
        skip_if: t.Callable[[IExecutionContext], bool] = None,
    ) -> DynamicModule:
        if storage and isinstance(storage, IThrottlerStorage):
            _provider = ProviderConfig(IThrottlerStorage, use_value=storage)
        elif storage:
            _provider = ProviderConfig(IThrottlerStorage, use_class=storage)
        else:
            _provider = ProviderConfig(
                IThrottlerStorage, use_class=ThrottlerStorageService
            )

        return DynamicModule(
            cls,
            providers=[
                _provider,
                ProviderConfig(
                    ThrottlerModuleOptions,
                    use_value=ThrottlerModuleOptions(
                        limit=limit,
                        ttl=ttl,
                        skip_if=skip_if,  # type:ignore[arg-type]
                    ),
                ),
            ],
        )
