# scrapers package – registry of all active scrapers
from scrapers.aljazeera import AlJazeeraRSSScraper
from scrapers.apnews import APNewsRSSScraper
from scrapers.reuters import ReutersRSSScraper
from scrapers.jpost import JPostRSSScraper
from scrapers.unnews import UNNewsRSSScraper
from scrapers.bbc import BBCNewsRSSScraper
from scrapers.cnn import CNNScraper
from scrapers.liveuamap import LiveUAMapScraper
from scrapers.npr import NPRRSSScraper

ALL_SCRAPERS = [
    AlJazeeraRSSScraper,
    APNewsRSSScraper,
    ReutersRSSScraper,
    JPostRSSScraper,
    UNNewsRSSScraper,
    BBCNewsRSSScraper,
    CNNScraper,
    LiveUAMapScraper,
    NPRRSSScraper,
]
