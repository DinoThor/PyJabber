from unittest.mock import MagicMock

import pytest
from test.Model_test import ModelTest


@pytest.fixture
def model():
    mock = MagicMock()
    mock.Credentials = ModelTest.Credentials
    mock.Roster = ModelTest.Roster
    mock.Pubsub = ModelTest.Pubsub
    mock.PubsubSubscribers = ModelTest.PubsubSubscribers
    mock.PubsubItems = ModelTest.PubsubItems
    mock.PendingSubs = ModelTest.PendingSubs
    yield mock

