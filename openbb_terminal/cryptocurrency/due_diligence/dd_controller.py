"""Cryptocurrency Due diligence Controller"""
__docformat__ = "numpy"

# pylint: disable=R0904, C0302, W0622, C0201, consider-using-dict-items
import argparse
import logging
from datetime import datetime, timedelta
from typing import List
from prompt_toolkit.completion import NestedCompleter

from openbb_terminal.cryptocurrency import cryptocurrency_helpers
from openbb_terminal import feature_flags as obbff
from openbb_terminal.cryptocurrency.overview import cryptopanic_model
from openbb_terminal.cryptocurrency.due_diligence import (
    binance_model,
    binance_view,
    ccxt_model,
    ccxt_view,
    coinbase_view,
    coinglass_model,
    coinbase_model,
    coinglass_view,
    coinpaprika_view,
    glassnode_model,
    glassnode_view,
    pycoingecko_view,
    messari_model,
    messari_view,
    santiment_view,
    cryptopanic_view,
)
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    EXPORT_BOTH_RAW_DATA_AND_FIGURES,
    EXPORT_ONLY_RAW_DATA_ALLOWED,
    check_positive,
    valid_date,
)
from openbb_terminal.menu import session
from openbb_terminal.parent_classes import CryptoBaseController
from openbb_terminal.rich_config import console, MenuText

logger = logging.getLogger(__name__)

FILTERS_VS_USD_BTC = ["usd", "btc"]


def check_cg_id(symbol: str):
    cg_id = cryptocurrency_helpers.get_coingecko_id(symbol)
    if not cg_id:
        print(f"\n{symbol} not found on CoinGecko")
        return ""
    return symbol


class DueDiligenceController(CryptoBaseController):
    """Due Diligence Controller class"""

    CHOICES_COMMANDS = [
        "load",
        "fundrate",
        "oi",
        "liquidations",
        "active",
        "change",
        "nonzero",
        "eb",
    ]

    SPECIFIC_CHOICES = {
        "cp": [
            "events",
            "twitter",
            "ex",
            "mkt",
            "ps",
            "basic",
        ],
        "cg": [
            "info",
            "market",
            "ath",
            "atl",
            "score",
            "web",
            "social",
            "bc",
            "dev",
        ],
        "bin": [
            "balance",
        ],
        "ccxt": ["ob", "trades"],
        "cb": ["stats"],
        "mes": ["mcapdom", "links", "rm", "tk", "pi", "mt", "team", "gov", "fr", "inv"],
        "san": ["gh"],
        "cpanic": ["news"],
    }

    DD_VIEWS_MAPPING = {
        "cg": pycoingecko_view,
        "cp": coinpaprika_view,
        "bin": binance_view,
        "mes": messari_view,
        "san": santiment_view,
        "cpanic": cryptopanic_view,
    }

    PATH = "/crypto/dd/"

    def __init__(
        self,
        symbol=None,
        source=None,
        queue: List[str] = None,
    ):
        """Constructor"""
        super().__init__(queue)

        for _, value in self.SPECIFIC_CHOICES.items():
            self.controller_choices.extend(value)

        self.source = source
        self.symbol = symbol
        self.messari_timeseries = []
        df_mt = messari_model.get_available_timeseries()
        self.ccxt_exchanges = ccxt_model.get_exchanges()

        if not df_mt.empty:
            self.messari_timeseries = df_mt.index.to_list()
        if session and obbff.USE_PROMPT_TOOLKIT:
            choices: dict = {c: {} for c in self.controller_choices}
            choices["ob"] = {c: None for c in self.ccxt_exchanges}
            choices["ob"]["-e"] = {c: None for c in self.ccxt_exchanges}
            choices["trades"] = {c: None for c in self.ccxt_exchanges}
            choices["trades"]["-e"] = {c: None for c in self.ccxt_exchanges}
            choices["active"]["-i"] = {
                c: None for c in glassnode_model.INTERVALS_ACTIVE_ADDRESSES
            }
            choices["change"] = {
                c: None for c in glassnode_model.GLASSNODE_SUPPORTED_EXCHANGES
            }
            choices["eb"] = {
                c: None for c in glassnode_model.GLASSNODE_SUPPORTED_EXCHANGES
            }
            choices["oi"]["-i"] = {c: None for c in coinglass_model.INTERVALS}
            choices["atl"]["--vs"] = {c: None for c in FILTERS_VS_USD_BTC}
            choices["ath"]["--vs"] = {c: None for c in FILTERS_VS_USD_BTC}
            choices["mkt"]["--vs"] = {c: None for c in coinpaprika_view.CURRENCIES}
            choices["mkt"]["-s"] = {c: None for c in coinpaprika_view.MARKET_FILTERS}
            choices["ex"]["-s"] = {c: None for c in coinpaprika_view.EX_FILTERS}
            choices["events"]["-s"] = {c: None for c in coinpaprika_view.EVENTS_FILTERS}
            choices["twitter"]["-s"] = {
                c: None for c in coinpaprika_view.TWEETS_FILTERS
            }
            choices["mt"] = {c: None for c in self.messari_timeseries}
            choices["mt"]["-i"] = {c: None for c in messari_model.INTERVALS_TIMESERIES}
            choices["mcapdom"]["-i"] = {
                c: None for c in messari_model.INTERVALS_TIMESERIES
            }
            choices["ps"]["--vs"] = {c: None for c in coinpaprika_view.CURRENCIES}
            choices["news"]["-k"] = {c: None for c in cryptopanic_model.CATEGORIES}
            choices["news"]["--filter"] = {c: None for c in cryptopanic_model.FILTERS}
            choices["news"]["-r"] = {c: None for c in cryptopanic_model.REGIONS}
            choices["news"]["-s"] = {c: None for c in cryptopanic_model.SORT_FILTERS}

            choices["support"] = self.SUPPORT_CHOICES
            choices["about"] = self.ABOUT_CHOICES

            self.completer = NestedCompleter.from_nested_dict(choices)

    def print_help(self):
        """Print help"""
        mt = MenuText("crypto/dd/", 120)
        mt.add_cmd("load")
        mt.add_raw("\n")
        mt.add_param("_symbol", self.symbol)
        mt.add_param("_source", "cg" if self.source != "" else "")
        mt.add_raw("\n")

        mt.add_info("_overview_")
        mt.add_cmd("info", "CoinGecko")
        mt.add_cmd("basic", "CoinPaprika")
        mt.add_cmd("ath", "CoinGecko")
        mt.add_cmd("atl", "CoinGecko")
        mt.add_cmd("web", "CoinGecko")
        mt.add_cmd("pi", "Messari")
        mt.add_cmd("gov", "Messari")
        mt.add_cmd("stats", "Coinbase")
        mt.add_cmd("bc", "CoinGecko")

        mt.add_info("_market_")
        mt.add_cmd("market", "CoinGecko")
        mt.add_cmd("mkt", "CoinPaprika")
        mt.add_cmd("balance", "Binance")
        mt.add_cmd("ex", "CoinPaprika")
        mt.add_cmd("oi", "Coinglass")
        mt.add_cmd("fundrate", "Coinglass")
        mt.add_cmd("liquidations", "Coinglass")
        mt.add_cmd("eb", "Glassnode")
        mt.add_cmd("trades", "CCXT")
        mt.add_cmd("ob", "CCXT")

        mt.add_info("_metrics_")
        mt.add_cmd("mcapdom", "Messari")
        mt.add_cmd("active", "Glassnode")
        mt.add_cmd("nonzero", "Glassnode")
        mt.add_cmd("change", "Glassnode")
        mt.add_cmd("ps", "CoinPaprika")
        mt.add_cmd("mt", "Messari")

        mt.add_info("_contributors_")
        mt.add_cmd("team", "Messari")
        mt.add_cmd("inv", "Messari")

        mt.add_info("_tokenomics_")
        mt.add_cmd("tk", "Messari")
        mt.add_cmd("fr", "Messari")

        mt.add_info("_roadmap_")
        mt.add_cmd("rm", "Messari")
        mt.add_cmd("events", "CoinPaprika")
        mt.add_cmd("news", "CryptoPanic")

        mt.add_info("_activity_")
        mt.add_cmd("links", "Messari")
        mt.add_cmd("social", "CoinGecko")
        mt.add_cmd("twitter", "CoinPaprika")
        mt.add_cmd("score", "CoinGecko")
        mt.add_cmd("dev", "CoinGecko")
        mt.add_cmd("gh", "Santiment")
        console.print(text=mt.menu_text, menu="Crypto - Due Diligence")

    def custom_reset(self):
        """Class specific component of reset command"""
        if self.symbol:
            return ["crypto", f"load {self.symbol}", "dd"]
        return []

    @log_start_end(log=logger)
    def call_nonzero(self, other_args: List[str]):
        """Process nonzero command"""

        if self.symbol.upper() in glassnode_model.GLASSNODE_SUPPORTED_ASSETS:
            parser = argparse.ArgumentParser(
                add_help=False,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                prog="nonzero",
                description="""
                    Display addresses with nonzero assets in a certain blockchain
                    [Source: https://glassnode.org]
                    Note that free api keys only allow fetching data with a 1y lag
                """,
            )

            parser.add_argument(
                "-s",
                "--since",
                dest="since",
                type=valid_date,
                help="Initial date. Default: 2 years ago",
                default=(datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d"),
            )

            parser.add_argument(
                "-u",
                "--until",
                dest="until",
                type=valid_date,
                help="Final date. Default: 1 year ago",
                default=(datetime.now() - timedelta(days=367)).strftime("%Y-%m-%d"),
            )

            ns_parser = self.parse_known_args_and_warn(
                parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
            )

            if ns_parser:
                glassnode_view.display_non_zero_addresses(
                    symbol=self.symbol.upper(),
                    start_date=int(datetime.timestamp(ns_parser.since)),
                    end_date=int(datetime.timestamp(ns_parser.until)),
                    export=ns_parser.export,
                )

        else:
            console.print("Glassnode source does not support this symbol\n")

    @log_start_end(log=logger)
    def call_stats(self, other_args):
        """Process stats command"""
        coin = self.symbol.upper()
        _, quotes = coinbase_model.show_available_pairs_for_given_symbol(coin)

        parser = argparse.ArgumentParser(
            prog="stats",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="Display coin stats",
        )

        parser.add_argument(
            "--vs",
            help="Quote currency (what to view coin vs)",
            dest="vs",
            type=str,
            default="USDT" if "USDT" in quotes else quotes[0],
            choices=quotes,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            pair = f"{coin}-{ns_parser.vs.upper()}"
            coinbase_view.display_stats(pair, ns_parser.export)

    @log_start_end(log=logger)
    def call_active(self, other_args: List[str]):
        """Process active command"""

        if self.symbol.upper() in glassnode_model.GLASSNODE_SUPPORTED_ASSETS:
            parser = argparse.ArgumentParser(
                add_help=False,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                prog="active",
                description="""
                    Display active blockchain addresses over time
                    [Source: https://glassnode.org]
                """,
            )

            parser.add_argument(
                "-i",
                "--interval",
                dest="interval",
                type=str,
                help="Frequency interval. Default: 24h",
                default="24h",
                choices=glassnode_model.INTERVALS_ACTIVE_ADDRESSES,
            )

            parser.add_argument(
                "-s",
                "--since",
                dest="since",
                type=valid_date,
                help="Initial date. Default: 1 year ago",
                default=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
            )

            parser.add_argument(
                "-u",
                "--until",
                dest="until",
                type=valid_date,
                help="Final date. Default: Today",
                default=(datetime.now()).strftime("%Y-%m-%d"),
            )

            ns_parser = self.parse_known_args_and_warn(
                parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
            )

            if ns_parser:
                glassnode_view.display_active_addresses(
                    symbol=self.symbol.upper(),
                    interval=ns_parser.interval,
                    start_date=int(datetime.timestamp(ns_parser.since)),
                    end_date=int(datetime.timestamp(ns_parser.until)),
                    export=ns_parser.export,
                )

        else:
            console.print("Glassnode source does not support this symbol\n")

    @log_start_end(log=logger)
    def call_change(self, other_args: List[str]):
        """Process change command"""

        if self.symbol.upper() in glassnode_model.GLASSNODE_SUPPORTED_ASSETS:
            parser = argparse.ArgumentParser(
                add_help=False,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                prog="change",
                description="""
                    Display active blockchain addresses over time
                    [Source: https://glassnode.org]
                    Note that free api keys only allow fetching data with a 1y lag
                """,
            )

            parser.add_argument(
                "-e",
                "--exchange",
                dest="exchange",
                type=str,
                help="Exchange to check change. Default: aggregated",
                default="aggregated",
                choices=glassnode_model.GLASSNODE_SUPPORTED_EXCHANGES,
            )

            parser.add_argument(
                "-s",
                "--since",
                dest="since",
                type=valid_date,
                help="Initial date. Default: 2 years ago",
                default=(datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d"),
            )

            parser.add_argument(
                "-u",
                "--until",
                dest="until",
                type=valid_date,
                help="Final date. Default: 1 year ago",
                default=(datetime.now() - timedelta(days=367)).strftime("%Y-%m-%d"),
            )

            if other_args:
                if not other_args[0][0] == "-":
                    other_args.insert(0, "-e")

            ns_parser = self.parse_known_args_and_warn(
                parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
            )

            if ns_parser:
                glassnode_view.display_exchange_net_position_change(
                    symbol=self.symbol.upper(),
                    exchange=ns_parser.exchange,
                    start_date=int(datetime.timestamp(ns_parser.since)),
                    end_date=int(datetime.timestamp(ns_parser.until)),
                    export=ns_parser.export,
                )
        else:
            console.print("Glassnode source does not support this symbol\n")

    @log_start_end(log=logger)
    def call_eb(self, other_args: List[str]):
        """Process eb command"""

        if self.symbol.upper() in glassnode_model.GLASSNODE_SUPPORTED_ASSETS:
            parser = argparse.ArgumentParser(
                add_help=False,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                prog="eb",
                description="""
                    Display active blockchain addresses over time
                    [Source: https://glassnode.org]
                    Note that free api keys only allow fetching data with a 1y lag
                """,
            )

            parser.add_argument(
                "-p",
                "--pct",
                dest="percentage",
                type=bool,
                help="Show percentage instead of stacked value. Default: False",
            )

            parser.add_argument(
                "-e",
                "--exchange",
                dest="exchange",
                type=str,
                help="Exchange to check change. Default: aggregated",
                default="aggregated",
                choices=glassnode_model.GLASSNODE_SUPPORTED_EXCHANGES,
            )

            parser.add_argument(
                "-s",
                "--since",
                dest="since",
                type=valid_date,
                help="Initial date. Default: 2 years ago",
                default=(datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d"),
            )

            parser.add_argument(
                "-u",
                "--until",
                dest="until",
                type=valid_date,
                help="Final date. Default: 1 year ago",
                default=(datetime.now() - timedelta(days=367)).strftime("%Y-%m-%d"),
            )

            if other_args and not other_args[0][0] == "-":
                other_args.insert(0, "-e")

            ns_parser = self.parse_known_args_and_warn(
                parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
            )

            if ns_parser:
                glassnode_view.display_exchange_balances(
                    symbol=self.symbol.upper(),
                    exchange=ns_parser.exchange,
                    start_date=int(datetime.timestamp(ns_parser.since)),
                    end_date=int(datetime.timestamp(ns_parser.until)),
                    percentage=ns_parser.percentage,
                    export=ns_parser.export,
                )

        else:
            console.print("Glassnode source does not support this symbol\n")

    @log_start_end(log=logger)
    def call_oi(self, other_args):
        """Process oi command"""
        assert isinstance(self.symbol, str)
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="oi",
            description="""
                Displays open interest by exchange for a certain asset
                [Source: https://coinglass.github.io/API-Reference/]
            """,
        )

        parser.add_argument(
            "-i",
            "--interval",
            dest="interval",
            type=int,
            help="Frequency interval. Default: 0",
            default=0,
            choices=coinglass_model.INTERVALS,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )

        if ns_parser:
            coinglass_view.display_open_interest(
                symbol=self.symbol.upper(),
                interval=ns_parser.interval,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_liquidations(self, other_args):
        """Process liquidations command"""
        assert isinstance(self.symbol, str)
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="liquidations",
            description="""
                Displays liquidations data for the loaded crypto asset
                [Source: https://coinglass.github.io/API-Reference/#liquidation-chart]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )

        if ns_parser:
            coinglass_view.display_liquidations(
                symbol=self.symbol.upper(),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_fundrate(self, other_args):
        """Process fundrate command"""
        assert isinstance(self.symbol, str)
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="fundrate",
            description="""
                Displays funding rate by exchange for a certain asset
                [Source: https://coinglass.github.io/API-Reference/]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )

        if ns_parser:
            coinglass_view.display_funding_rate(
                symbol=self.symbol.upper(),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_info(self, other_args):
        """Process info command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="info",
            description="""
                    Shows basic information about loaded coin like:
                    Name, Symbol, Description, Market Cap, Public Interest, Supply, and Price related metrics
                    """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            if self.symbol:
                pycoingecko_view.display_info(
                    symbol=self.symbol,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_market(self, other_args):
        """Process market command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="market",
            description="""
            Market data for loaded coin. There you find metrics like:
            Market Cap, Supply, Circulating Supply, Price, Volume and many others.""",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            cg_id = check_cg_id(self.symbol)
            if cg_id:
                pycoingecko_view.display_market(cg_id, ns_parser.export)

    @log_start_end(log=logger)
    def call_web(self, other_args):
        """Process web command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="web",
            description="""Websites found for given Coin. You can find there urls to
                                homepage, forum, announcement site and others.""",
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            if self.symbol:
                pycoingecko_view.display_web(
                    self.symbol,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_social(self, other_args):
        """Process social command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="social",
            description="""Shows social media corresponding to loaded coin. You can find there name of
            telegram channel, urls to twitter, reddit, bitcointalk, facebook and discord.""",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            cg_id = check_cg_id(self.symbol)
            if cg_id:
                pycoingecko_view.display_social(cg_id, export=ns_parser.export)

    @log_start_end(log=logger)
    def call_dev(self, other_args):
        """Process dev command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="dev",
            description="""
            Developers data for loaded coin. If the development data is available you can see
            how the code development of given coin is going on.
            There are some statistics that shows number of stars, forks, subscribers, pull requests,
            commits, merges, contributors on github.""",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            cg_id = check_cg_id(self.symbol)
            if cg_id:
                pycoingecko_view.display_dev(cg_id, ns_parser.export)

    @log_start_end(log=logger)
    def call_ath(self, other_args):
        """Process ath command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="ath",
            description="""All time high data for loaded coin""",
        )

        parser.add_argument(
            "--vs",
            dest="vs",
            help="currency",
            default="usd",
            choices=FILTERS_VS_USD_BTC,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            cg_id = check_cg_id(self.symbol)
            if cg_id:
                pycoingecko_view.display_ath(cg_id, ns_parser.vs, ns_parser.export)

    @log_start_end(log=logger)
    def call_atl(self, other_args):
        """Process atl command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="atl",
            description="""All time low data for loaded coin""",
        )

        parser.add_argument(
            "--vs",
            dest="vs",
            help="currency",
            default="usd",
            choices=FILTERS_VS_USD_BTC,
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            cg_id = check_cg_id(self.symbol)
            if cg_id:
                pycoingecko_view.display_atl(cg_id, ns_parser.vs, ns_parser.export)

    @log_start_end(log=logger)
    def call_score(self, other_args):
        """Process score command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="score",
            description="""
            In this view you can find different kind of scores for loaded coin.
            Those scores represents different rankings, sentiment metrics, some user stats and others.
            You will see CoinGecko scores, Developer Scores, Community Scores, Sentiment, Reddit scores
            and many others.""",
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            cg_id = check_cg_id(self.symbol)
            if cg_id:
                pycoingecko_view.display_score(cg_id, ns_parser.export)

    @log_start_end(log=logger)
    def call_bc(self, other_args):
        """Process bc command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="bc",
            description="""
            Blockchain explorers URLs for loaded coin. Those are sites like etherescan.io or polkascan.io
            in which you can see all blockchain data e.g. all txs, all tokens, all contracts...
                                """,
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            cg_id = check_cg_id(self.symbol)
            if cg_id:
                pycoingecko_view.display_bc(cg_id, ns_parser.export)

    @log_start_end(log=logger)
    def call_ob(self, other_args):
        """Process order book command"""
        parser = argparse.ArgumentParser(
            prog="ob",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="Get the order book for selected coin",
        )

        parser.add_argument(
            "-e",
            "--exchange",
            help="Exchange to search for order book",
            dest="exchange",
            type=str,
            default="binance",
            choices=self.ccxt_exchanges,
        )

        parser.add_argument(
            "--vs",
            help="Quote currency (what to view coin vs)",
            dest="vs",
            type=str.lower,
            default="usdt",
            choices=["usdt", "usdc", "btc"],
        )

        if other_args and not other_args[0][0] == "-":
            other_args.insert(0, "-e")

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )

        if ns_parser:
            ccxt_view.display_order_book(
                ns_parser.exchange,
                symbol=self.symbol,
                vs=ns_parser.vs,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_trades(self, other_args):
        """Process trades command"""
        parser = argparse.ArgumentParser(
            prog="trades",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="Get the latest trades for selected coin",
        )

        parser.add_argument(
            "-e",
            "--exchange",
            help="Exchange to search for order book",
            dest="exchange",
            type=str,
            default="binance",
            choices=self.ccxt_exchanges,
        )

        parser.add_argument(
            "--vs",
            help="Quote currency (what to view coin vs)",
            dest="vs",
            type=str.lower,
            default="usdt",
            choices=["usdt", "usdc", "btc"],
        )

        if other_args and not other_args[0][0] == "-":
            other_args.insert(0, "-e")

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES, limit=10
        )

        if ns_parser:
            ccxt_view.display_trades(
                ns_parser.exchange,
                symbol=self.symbol,
                vs=ns_parser.vs,
                export=ns_parser.export,
                limit=ns_parser.limit,
            )

    @log_start_end(log=logger)
    def call_balance(self, other_args):
        """Process balance command"""
        coin = self.symbol.upper()
        _, quotes = binance_model.show_available_pairs_for_given_symbol(coin)

        parser = argparse.ArgumentParser(
            prog="balance",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="Display balance",
        )

        parser.add_argument(
            "--vs",
            help="Quote currency (what to view coin vs)",
            dest="vs",
            type=str,
            default="USDT",
            choices=quotes,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            binance_view.display_balance(
                to_symbol=coin, from_symbol=ns_parser.vs, export=ns_parser.export
            )

    @log_start_end(log=logger)
    def call_ps(self, other_args):
        """Process ps command"""
        parser = argparse.ArgumentParser(
            prog="ps",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""Get price and supply related metrics for given coin.""",
        )

        parser.add_argument(
            "--vs",
            help="Quoted currency. Default USD",
            dest="vs",
            default="USD",
            type=str,
            choices=coinpaprika_view.CURRENCIES,
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if self.symbol:
                coinpaprika_view.display_price_supply(
                    self.symbol,
                    ns_parser.vs,
                    ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_basic(self, other_args):
        """Process basic command"""
        parser = argparse.ArgumentParser(
            prog="basic",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""Get basic information for coin. Like:
                name, symbol, rank, type, description, platform, proof_type,
                contract, tags, parent""",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if self.symbol:
                coinpaprika_view.display_basic(
                    self.symbol,
                    ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_mkt(self, other_args):
        """Process mkt command"""
        parser = argparse.ArgumentParser(
            prog="mkt",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""Get all markets found for given coin.
                You can display only N number of markets with --limt parameter.
                You can sort data by pct_volume_share, exchange, pair, trust_score, volume, price --sort parameter
                and also with --descend flag to sort descending.
                You can use additional flag --urls to see urls for each market
                Displays:
                    exchange, pair, trust_score, volume, price, pct_volume_share,""",
        )

        parser.add_argument(
            "--vs",
            help="Quoted currency. Default USD",
            dest="vs",
            default="USD",
            type=str,
            choices=coinpaprika_view.CURRENCIES,
        )

        parser.add_argument(
            "-l",
            "--limit",
            default=20,
            dest="limit",
            help="Limit of records",
            type=check_positive,
        )

        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            type=str,
            help="Sort by given column. Default: pct_volume_share",
            default="pct_volume_share",
            choices=coinpaprika_view.MARKET_FILTERS,
        )

        parser.add_argument(
            "--descend",
            action="store_false",
            help="Flag to sort in descending order (lowest first)",
            dest="descend",
            default=False,
        )

        parser.add_argument(
            "-u",
            "--urls",
            dest="urls",
            action="store_true",
            help="""Flag to show urls. If you will use that flag you will see only:
                exchange, pair, trust_score, market_url columns""",
            default=False,
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if self.symbol:
                coinpaprika_view.display_markets(
                    symbol=self.symbol,
                    currency=ns_parser.vs,
                    limit=ns_parser.limit,
                    sortby=ns_parser.sortby,
                    ascend=not ns_parser.descend,
                    links=ns_parser.urls,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_ex(self, other_args):
        """Process ex command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="ex",
            description="""Get all exchanges found for given coin.
                You can display only top N number of exchanges with --top parameter.
                You can sort data by  id, name, adjusted_volume_24h_share, fiats --sort parameter
                and also with --descend flag to sort descending.
                Displays:
                    id, name, adjusted_volume_24h_share, fiats""",
        )

        parser.add_argument(
            "-l",
            "--limit",
            default=10,
            dest="limit",
            help="Limit of records",
            type=check_positive,
        )

        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            type=str,
            help="Sort by given column. Default: date",
            default="adjusted_volume_24h_share",
            choices=coinpaprika_view.EX_FILTERS,
        )

        parser.add_argument(
            "--descend",
            action="store_false",
            help="Flag to sort in descending order (lowest first)",
            dest="descend",
            default=False,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if self.symbol:
                coinpaprika_view.display_exchanges(
                    symbol=self.symbol,
                    limit=ns_parser.limit,
                    sortby=ns_parser.sortby,
                    ascend=not ns_parser.descend,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_events(self, other_args):
        """Process events command"""
        parser = argparse.ArgumentParser(
            prog="events",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""
            Show information about most important coins events. Most of coins doesn't have any events.
            You can display only top N number of events with --limit parameter.
            You can sort data by id, date , date_to, name, description, is_conference --sort parameter
            and also with --descend flag to sort descending.
            You can use additional flag --urls to see urls for each event
            Displays:
                date , date_to, name, description, is_conference, link, proof_image_link""",
        )

        parser.add_argument(
            "-l",
            "--limit",
            default=10,
            dest="limit",
            help="Limit of records",
            type=check_positive,
        )

        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            type=str,
            help="Sort by given column. Default: date",
            default="date",
            choices=coinpaprika_view.EVENTS_FILTERS,
        )

        parser.add_argument(
            "--descend",
            action="store_false",
            help="Flag to sort in descending order (lowest first)",
            dest="descend",
            default=False,
        )

        parser.add_argument(
            "-u",
            "--urls",
            dest="urls",
            action="store_true",
            help="Flag to show urls. If you will use that flag you will see only date, name, link columns",
            default=False,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if self.symbol:
                coinpaprika_view.display_events(
                    symbol=self.symbol,
                    limit=ns_parser.limit,
                    sortby=ns_parser.sortby,
                    ascend=not ns_parser.descend,
                    links=ns_parser.urls,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_twitter(self, other_args):
        """Process twitter command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="twitter",
            description="""Show last 10 tweets for given coin.
                You can display only N number of tweets with --limit parameter.
                You can sort data by date, user_name, status, retweet_count, like_count --sort parameter
                and also with --descend flag to sort descending.
                Displays:
                    date, user_name, status, retweet_count, like_count
                """,
        )

        parser.add_argument(
            "-l",
            "--limit",
            default=10,
            dest="limit",
            help="Limit of records",
            type=check_positive,
        )

        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            type=str,
            help="Sort by given column. Default: date",
            default="date",
            choices=coinpaprika_view.TWEETS_FILTERS,
        )

        parser.add_argument(
            "--descend",
            action="store_false",
            help="Flag to sort in descending order (lowest first)",
            dest="descend",
            default=False,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if self.symbol:
                coinpaprika_view.display_twitter(
                    symbol=self.symbol,
                    limit=ns_parser.limit,
                    sortby=ns_parser.sortby,
                    ascend=not ns_parser.descend,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_mcapdom(self, other_args: List[str]):
        """Process mcapdom command"""

        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="mcapdom",
            description="""
                Display asset's percentage share of total crypto circulating market cap
                [Source: https://messari.io]
            """,
        )

        parser.add_argument(
            "-i",
            "--interval",
            dest="interval",
            type=str,
            help="Frequency interval. Default: 1d",
            default="1d",
            choices=messari_model.INTERVALS_TIMESERIES,
        )

        parser.add_argument(
            "-s",
            "--start",
            dest="start",
            type=valid_date,
            help="Initial date. Default: A year ago",
            default=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        )

        parser.add_argument(
            "-end",
            "--end",
            dest="end",
            type=valid_date,
            help="End date. Default: Today",
            default=datetime.now().strftime("%Y-%m-%d"),
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )

        if ns_parser:
            messari_view.display_marketcap_dominance(
                symbol=self.symbol.upper(),
                interval=ns_parser.interval,
                start_date=ns_parser.start,
                end_date=ns_parser.end,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_links(self, other_args: List[str]):
        """Process links command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="links",
            description="""
                Display asset's links
                [Source: https://messari.io]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            messari_view.display_links(
                symbol=self.symbol.upper(),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_gh(self, other_args: List[str]):
        """Process gh command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="gh",
            description="""
                Display github activity over time for a given coin.
                Github activity includes the following actions: creating a Pull Request, an Issue,
                commenting on an issue / PR, and many more.

                See detailed definition at https://academy.santiment.net/metrics/development-activity/

                [Source: https://santiment.net/]
                """,
        )
        parser.add_argument(
            "-i",
            "--interval",
            dest="interval",
            type=str,
            help="Frequency interval. Default: 1d",
            default="1d",
        )

        parser.add_argument(
            "-d",
            "--dev",
            dest="dev",
            type=bool,
            help="Filter only for development activity. Default: False",
            default=False,
        )

        parser.add_argument(
            "-s",
            "--start",
            dest="start",
            type=valid_date,
            help="Initial date. Default: A year ago",
            default=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        )

        parser.add_argument(
            "-end",
            "--end",
            dest="end",
            type=valid_date,
            help="End date. Default: Today",
            default=datetime.now().strftime("%Y-%m-%d"),
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )

        if ns_parser:
            santiment_view.display_github_activity(
                symbol=self.symbol.upper(),
                interval=ns_parser.interval,
                dev_activity=ns_parser.dev,
                start=ns_parser.start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                end=ns_parser.end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

    @log_start_end(log=logger)
    def call_rm(self, other_args: List[str]):
        """Process rm command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="rm",
            description="""
                Display asset's roadmap
                [Source: https://messari.io]
            """,
        )

        parser.add_argument(
            "--descend",
            action="store_true",
            help="Flag to sort in descending order (lowest first)",
            dest="descend",
            default=False,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED, limit=5
        )

        if ns_parser:
            messari_view.display_roadmap(
                ascend=not ns_parser.descend,
                symbol=self.symbol.upper(),
                limit=ns_parser.limit,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_tk(self, other_args: List[str]):
        """Process tk command"""

        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="tk",
            description="""
                Display asset's tokenomics
                [Source: https://messari.io]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            if self.symbol:
                messari_view.display_tokenomics(
                    symbol=self.symbol.upper(),
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_pi(self, other_args: List[str]):
        """Process pi command"""

        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="pi",
            description="""
                Display asset's project info
                [Source: https://messari.io]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            messari_view.display_project_info(
                symbol=self.symbol.upper(),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_team(self, other_args: List[str]):
        """Process team command"""

        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="team",
            description="""
                Display asset's team
                [Source: https://messari.io]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            messari_view.display_team(
                symbol=self.symbol.upper(),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_inv(self, other_args: List[str]):
        """Process inv command"""

        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="inv",
            description="""
                Display asset's investors
                [Source: https://messari.io]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            messari_view.display_investors(
                symbol=self.symbol.upper(),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_fr(self, other_args: List[str]):
        """Process fr command"""

        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="fr",
            description="""
                Display asset's fundraising details
                [Source: https://messari.io]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            messari_view.display_fundraising(
                symbol=self.symbol.upper(),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_gov(self, other_args: List[str]):
        """Process gov command"""

        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="gov",
            description="""
                Display asset's governance
                [Source: https://messari.io]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            messari_view.display_governance(
                symbol=self.symbol.upper(),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_mt(self, other_args: List[str]):
        """Process mt command"""

        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="mt",
            description="""
                Display messari timeseries
                [Source: https://messari.io]
            """,
        )

        parser.add_argument(
            "--list",
            action="store_true",
            help="Flag to show available timeseries",
            dest="list",
            default=False,
        )

        parser.add_argument(
            "-t",
            "--timeseries",
            dest="timeseries",
            type=str,
            help="Messari timeseries id",
            default="",
        )

        parser.add_argument(
            "-i",
            "--interval",
            dest="interval",
            type=str,
            help="Frequency interval",
            default="1d",
            choices=messari_model.INTERVALS_TIMESERIES,
        )
        parser.add_argument(
            "-s",
            "--start",
            dest="start",
            type=valid_date,
            help="Initial date. Default: A year ago",
            default=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        )

        parser.add_argument(
            "-end",
            "--end",
            dest="end",
            type=valid_date,
            help="End date. Default: Today",
            default=datetime.now().strftime("%Y-%m-%d"),
        )
        parser.add_argument(
            "--include-paid",
            action="store_true",
            help="Flag to show both paid and free sources",
            dest="include_paid",
            default=False,
        )

        parser.add_argument(
            "-q",
            "--query",
            type=str,
            dest="query",
            nargs="+",
            help="Query to search across all messari timeseries",
            default="",
        )

        if other_args and not other_args[0][0] == "-":
            other_args.insert(0, "-t")

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES, limit=10
        )

        if ns_parser:
            if (
                ns_parser.timeseries
                and ns_parser.timeseries not in self.messari_timeseries
            ):
                console.print("\nTimeseries {ns_parser.timeseries} not found")
                return
            if ns_parser.list or ns_parser.query or ns_parser.timeseries == "":
                messari_view.display_messari_timeseries_list(
                    ns_parser.limit,
                    " ".join(ns_parser.query),
                    not ns_parser.include_paid,
                    ns_parser.export,
                )
            else:
                messari_view.display_messari_timeseries(
                    timeseries_id=ns_parser.timeseries,
                    symbol=self.symbol.upper(),
                    interval=ns_parser.interval,
                    start_date=ns_parser.start,
                    end_date=ns_parser.end,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_news(self, other_args):
        """Process news command"""
        parser = argparse.ArgumentParser(
            prog="news",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""Display most recent news on the given coin from CryptoPanic aggregator platform.
            [Source: https://cryptopanic.com/]""",
        )

        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=check_positive,
            help="display N number records",
            default=10,
        )

        parser.add_argument(
            "-k",
            "--kind",
            dest="kind",
            type=str,
            help="Filter by category of news. Available values: news or media.",
            default="news",
            choices=cryptopanic_model.CATEGORIES,
        )

        parser.add_argument(
            "--filter",
            dest="filter",
            type=str,
            help="Filter by kind of news. From: rising|hot|bullish|bearish|important|saved|lol",
            default=None,
            required=False,
            choices=cryptopanic_model.FILTERS,
        )

        parser.add_argument(
            "-r",
            "--region",
            dest="region",
            type=str,
            help=(
                "Filter news by regions. Available regions are: en (English), de (Deutsch), nl"
                " (Dutch), es (Español), fr (Français), it (Italiano), pt (Português), ru "
                "(Русский)"
            ),
            default="en",
            choices=cryptopanic_model.REGIONS,
        )

        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            type=str,
            help="Sort by given column. Default: published_at",
            default="published_at",
            choices=cryptopanic_model.SORT_FILTERS,
        )

        parser.add_argument(
            "--descend",
            action="store_false",
            help="Flag to sort in descending order (lowest first)",
            dest="descend",
            default=True,
        )

        parser.add_argument(
            "-u",
            "--urls",
            dest="urls",
            action="store_false",
            help="Flag to disable urls. Hides column with URL.",
            default=True,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            cryptopanic_view.display_news(
                limit=ns_parser.limit,
                source=self.source,
                currency=self.symbol,
                export=ns_parser.export,
                ascend=not ns_parser.descend,
                post_kind=ns_parser.kind,
                filter_=ns_parser.filter,
                region=ns_parser.region,
            )
