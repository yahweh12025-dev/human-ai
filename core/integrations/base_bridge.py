from abc import ABC, abstractmethod

class BridgeInterface(ABC):
    @abstractmethod
    def initialize(self, query_params):
        """Initialize bridge with query parameters"""
        raise NotImplementedError()

    @abstractmethod
    def query(self, data_source, params):
        """Execute query against data source"""
        raise NotImplementedError()

    @abstractmethod
    def retrieve_data(self, results):
        """Process and return retrieved data"""
        raise NotImplementedError()

    @abstractmethod
    def handle_error(self, error):
        """Standardized error handling"""
        raise NotImplementedError()

    @abstractmethod
    def close(self):
        """Close any connections"""
        raise NotImplementedError()