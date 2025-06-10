import pickle
import numpy as np
import time

def save_tracker(model, filepath="tracker.pkl"):
    """Save YOLOv8 BoT-SORT tracker state to disk"""
    try:
        data = []
        if hasattr(model, 'predictor') and model.predictor.trackers:
            for tracker in model.predictor.trackers:
                if tracker is not None:
                    tracks = []
                    if hasattr(tracker, 'tracked_stracks'):
                        for t in tracker.tracked_stracks:
                            # BoT-SORT specific attributes
                            features = getattr(t, 'curr_feat', None)
                            if features is not None:
                                features = features.tolist() if hasattr(features, 'tolist') else None
                            
                            tracks.append((
                                t.track_id,
                                tuple(t.tlwh.tolist()),
                                t.score,
                                t.mean.tolist(),
                                t.covariance.tolist(),
                                features,
                                getattr(t, 'hits', 0),
                                getattr(t, 'age', 0),
                                getattr(t, 'time_since_update', 0)
                            ))
                    
                    data.append((
                        getattr(tracker, 'frame_id', 0),
                        getattr(tracker, '_count', 0),
                        getattr(tracker, 'track_len', 30),
                        getattr(tracker, 'proximity_thresh', 0.5),
                        getattr(tracker, 'appearance_thresh', 0.25),
                        tracks,
                        time.time()
                    ))
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        return True
    except:
        return False

def load_tracker(model, filepath="tracker.pkl"):
    """Load YOLOv8 BoT-SORT tracker state from disk"""
    try:
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        if hasattr(model, 'predictor') and model.predictor.trackers:
            for i, tracker_data in enumerate(data):
                if i < len(model.predictor.trackers):
                    tracker = model.predictor.trackers[i]
                    if tracker is not None:
                        frame_id, count, track_len, prox_thresh, app_thresh, tracks, timestamp = tracker_data
                        
                        # Check if save is too old (more than 1 minute)
                        if time.time() - timestamp > 60:
                            return False
                        
                        # Restore BoT-SORT tracker state
                        if hasattr(tracker, 'frame_id'):
                            tracker.frame_id = frame_id
                        if hasattr(tracker, '_count'):
                            tracker._count = count
                        if hasattr(tracker, 'track_len'):
                            tracker.track_len = track_len
                        if hasattr(tracker, 'proximity_thresh'):
                            tracker.proximity_thresh = prox_thresh
                        if hasattr(tracker, 'appearance_thresh'):
                            tracker.appearance_thresh = app_thresh
                        
                        # Restore tracks
                        if hasattr(tracker, 'tracked_stracks') and tracks:
                            tracker.tracked_stracks = []
                            
                            for track_data in tracks:
                                track_id, tlwh, score, mean, covariance, features, hits, age, time_since_update = track_data
                                
                                # Create track object
                                if hasattr(tracker, 'STrack'):
                                    track = tracker.STrack(np.array(tlwh), score)
                                    track.track_id = track_id
                                    track.mean = np.array(mean)
                                    track.covariance = np.array(covariance)
                                    track.hits = hits
                                    track.age = age
                                    track.time_since_update = time_since_update
                                    
                                    # Restore ReID features if available
                                    if features is not None:
                                        track.curr_feat = np.array(features)
                                    
                                    tracker.tracked_stracks.append(track)
        return True
    except Exception as e:
        print(e)
        return False