from datetime import datetime, time as dtime
from unittest.mock import patch
from bot.scheduler import scheduler, schedule_watch, realtime_job
from bot.models import Watch


def test_rt_job_added():
    """Test that real-time job is added for rt mode watch."""
    w = Watch(id=99, user_id=1, keywords="test", asin="B01234XYZ", mode="rt")
    schedule_watch(w)
    assert scheduler.get_job("rt:99") is not None


def test_daily_job_added():
    """Test that daily job is added for daily mode watch."""
    w = Watch(id=100, user_id=2, keywords="test", asin="B01234ABC", mode="daily")
    schedule_watch(w)
    assert scheduler.get_job("daily:2") is not None


def test_job_replacement():
    """Test that jobs are replaced when scheduling multiple times."""
    # Create first watch for user
    w1 = Watch(id=101, user_id=3, keywords="test1", asin="B01234DEF", mode="daily")
    schedule_watch(w1)
    job1 = scheduler.get_job("daily:3")
    assert job1 is not None
    
    # Create second watch for same user (should replace job)
    w2 = Watch(id=102, user_id=3, keywords="test2", asin="B01234GHI", mode="daily")
    schedule_watch(w2)
    job2 = scheduler.get_job("daily:3")
    
    # Job should exist and be the same ID (replaced)
    assert job2 is not None
    assert job1.id == job2.id == "daily:3"


def test_quiet_hours_logic():
    """Test that realtime_job respects quiet hours (23:00-08:00 IST)."""
    
    # Test during quiet hours (23:30) - should return early
    with patch('bot.scheduler.datetime') as mock_datetime, \
         patch('bot.scheduler.Session') as mock_session:
        
        mock_datetime.now.return_value.time.return_value = dtime(23, 30)
        
        # Should return early without database access
        result = realtime_job(999)
        assert result is None
        # Verify no database session was created during quiet hours
        mock_session.assert_not_called()
    
    # Test during active hours (10:00) - should attempt processing  
    with patch('bot.scheduler.datetime') as mock_datetime, \
         patch('bot.scheduler.Session') as mock_session:
        
        mock_datetime.now.return_value.time.return_value = dtime(10, 0)
        mock_session.return_value.__enter__.return_value.get.return_value = None
        
        # Should attempt to process and access database
        result = realtime_job(999)
        assert result is None
        # Verify database session was created during active hours
        mock_session.assert_called_once()
    
    # Test edge cases
    with patch('bot.scheduler.datetime') as mock_datetime, \
         patch('bot.scheduler.Session') as mock_session:
        
        # Just before quiet hours (22:59) - should process
        mock_datetime.now.return_value.time.return_value = dtime(22, 59)
        mock_session.return_value.__enter__.return_value.get.return_value = None
        
        result = realtime_job(999)
        assert result is None
        assert mock_session.called
    
    with patch('bot.scheduler.datetime') as mock_datetime, \
         patch('bot.scheduler.Session') as mock_session:
        
        # Just after quiet hours (08:01) - should process
        mock_datetime.now.return_value.time.return_value = dtime(8, 1) 
        mock_session.return_value.__enter__.return_value.get.return_value = None
        
        result = realtime_job(999)
        assert result is None
        assert mock_session.called