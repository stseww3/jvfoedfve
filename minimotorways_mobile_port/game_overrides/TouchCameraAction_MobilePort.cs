using Factory;
using Motorways.Audio;
using Motorways.Views;
using UnityEngine;

namespace Motorways.Actions;

/// <summary>
/// Mobile port upgrade of TouchCameraAction + CameraView pinch extension:
///   1. Supports 1-finger tap focus into edit mode, respecting the Touch Auto-Zoom
///      toggle (_player.IsZoomEnabled / "TouchZoomEnabled" in MotorwaysDeviceSettings).
///   2. Supports 2-finger pinch-to-zoom in and out simultaneously with 2-finger
///      midpoint panning between MinZoom and MaxZoom.
///   3. Cancels any in-progress 1-finger road draw (MakeExclusive) as soon as a
///      second finger touches down, preventing stray road segments on pinch.
///   4. Scales tap distance threshold with screen density for high-DPI mobile screens
///      such as Samsung Galaxy A72 (2400x1080 @ 407 PPI).
/// </summary>
public class TouchCameraAction : MotorwaysPlayerAction
{
	[Dependency]
	private CameraView _cameraView;

	[Dependency]
	protected IAudioSystem _audioSystem;

	[Dependency]
	protected ActivePlayer _player;

	[Dependency]
	private PlayerActionController _playerActionController;

	private Vector2 _initialScreenPosition;
	private Vector2 _currentScreenPosition;
	private Vector2 _panOriginCameraPosition;
	private Vector2 _panOriginWorldPosition;
	private bool _isPanning;
	private bool _isPinching;
	private float _initialPinchDistance;
	private float _initialPinchOrthoZoom;

	private float _tapTimeThreshold = 1f;
	private float _tapDistanceCoefficient = 0.5f;
	private const float MinPinchFingerSeparationPixels = 12f;

	public override void OnActionBegin(float timestamp)
	{
		_playerActionController.CancelAllActions();
		base.OnActionBegin(timestamp);
		_initialScreenPosition = GetPointerScreenPosition();
		_currentScreenPosition = _initialScreenPosition;
		_isPanning = false;
		_isPinching = false;
		_initialPinchDistance = 0f;
		_initialPinchOrthoZoom = 0f;
		PlayerAction.Log.Info("Beginning TouchCameraAction from {0}.", _initialScreenPosition);
	}

	public override void Tick(float frameTime)
	{
		base.Tick(frameTime);
		Vector2 pointerScreenPosition = GetPointerScreenPosition();

		if (_inputState.TouchCount >= 2 &&
		    _inputState.TryGetTouch(0, out IPointerState touch0) &&
		    _inputState.TryGetTouch(1, out IPointerState touch1) &&
		    touch0 != null && touch1 != null)
		{
			Vector2 pos0 = touch0.Position;
			Vector2 pos1 = touch1.Position;
			Vector2 midpoint = (pos0 + pos1) * 0.5f;
			float pinchDistance = Vector2.Distance(pos0, pos1);

			if (!_isPanning)
			{
				_panOriginCameraPosition = _cameraView.DesiredPosition;
				_panOriginWorldPosition = _tilemapView.GetWorldPositionFromScreenPosition(midpoint);
				_initialPinchDistance = Mathf.Max(pinchDistance, MinPinchFingerSeparationPixels);
				_initialPinchOrthoZoom = (_cameraView.playerOrthoZoom > 0f)
					? _cameraView.playerOrthoZoom
					: _cameraView.DesiredZoom;
				_isPanning = true;
				_isPinching = pinchDistance >= MinPinchFingerSeparationPixels;
				PlayerAction.Log.Info("Beginning 2-finger pinch/pan at midpoint {0} (dist={1}, world={2}).",
					midpoint, pinchDistance, _panOriginWorldPosition);
				if (!base.IsExclusive)
				{
					MakeExclusive();
				}
			}
			else
			{
				if (pinchDistance >= MinPinchFingerSeparationPixels && _initialPinchDistance >= MinPinchFingerSeparationPixels)
				{
					float zoomRatio = _initialPinchDistance / pinchDistance;
					float targetOrthoZoom = _initialPinchOrthoZoom * zoomRatio;
					ApplyPinchAndPanToCamera(targetOrthoZoom, _panOriginWorldPosition, midpoint);
				}
				else
				{
					_cameraView.ApplyPlayerPanPosition(_panOriginWorldPosition, midpoint);
				}
			}

			_currentScreenPosition = midpoint;
			return;
		}

		// If one finger lifted after a 2-finger pinch/pan, keep _isPanning = true so releasing
		// the remaining finger does not trigger a 1-finger tap focus toggle.
		_currentScreenPosition = pointerScreenPosition;
	}

	private void ApplyPinchAndPanToCamera(float targetOrthoZoom, Vector2 anchorWorldPosition, Vector2 midpointScreenPosition)
	{
		float minZoom = Mathf.Min(_cameraView.MinZoom, 5f);
		float maxZoom = Mathf.Max(_cameraView.MaxZoom, minZoom);
		float clampedZoom = Mathf.Clamp(targetOrthoZoom, minZoom, maxZoom);

		_cameraView.playerOrthoZoom = clampedZoom;

		// Reconcile edit-mode grid and draw buttons when pinching in/out across the focus threshold
		bool shouldBeZoomedIn = clampedZoom < maxZoom * 0.95f;
		if (shouldBeZoomedIn && !_cameraView.IsFocussedIn && _cameraView.CanChangeFocus)
		{
			_cameraView.FocusOnWorldPosition(anchorWorldPosition, CameraView.CameraFocusOffsetType.MaintainScreenPosition);
			_cameraView.playerOrthoZoom = clampedZoom;
			SetWorldGridVisible(visible: true);
			_gameUI.SetDrawButtonsVisible(visible: true);
			_tilemapView.viewMode = TilemapView.ViewMode.Edit;
		}
		else if (!shouldBeZoomedIn && _cameraView.IsFocussedIn && clampedZoom >= maxZoom * 0.99f)
		{
			SetWorldGridVisible(visible: false);
			SetMotorwayGridVisible(visible: false);
			_tilemapView.viewMode = TilemapView.ViewMode.Normal;
			_cameraView.ResetPlayerViewport();
			_gameUI.SetDrawButtonsVisible(visible: false);
			return;
		}

		_cameraView.ApplyPlayerPanPosition(anchorWorldPosition, midpointScreenPosition);
	}

	public override void ObserveInput(float timestamp, InputEvent inputEvent, bool overUI)
	{
		if (inputEvent.ButtonState != InputEventButtonState.JustUp)
		{
			return;
		}
		Vector2 pointerPosition = inputEvent.PointerPosition;
		float maxTapPixels = _tilemapView.ScreenDistanceBetweenTiles * _tapDistanceCoefficient;
		float dpi = (Screen.dpi > 20f && Screen.dpi < 1000f) ? Screen.dpi : 407f;
		float minDensityTapSlop = 12f * (dpi / 160f);
		if (maxTapPixels < minDensityTapSlop)
		{
			maxTapPixels = minDensityTapSlop;
		}

		if (!_isPanning && !_isPinching &&
		    Vector2.Distance(pointerPosition, _initialScreenPosition) < maxTapPixels &&
		    timestamp - timeCreated <= _tapTimeThreshold)
		{
			if (_inputState.TouchCount == 1 && _cameraView.CanChangeFocus)
			{
				if (!_cameraView.IsFocussedIn)
				{
					SetWorldGridVisible(visible: true);
					// Touch Auto-Zoom Toggle: when ON, zoom into tapped area; when OFF, enter edit mode without zooming
					if (_player.IsZoomEnabled)
					{
						_cameraView.FocusOnWorldPosition(_tilemapView.GetWorldPositionFromScreenPosition(pointerPosition), CameraView.CameraFocusOffsetType.MaintainScreenPosition);
					}
					else
					{
						_cameraView.FocusOnWorldPositionWithoutZoom(_tilemapView.GetWorldPositionFromScreenPosition(pointerPosition), CameraView.CameraFocusOffsetType.MaintainScreenPosition);
					}
					_gameUI.SetDrawButtonsVisible(visible: true);
					_tilemapView.viewMode = TilemapView.ViewMode.Edit;
					_audioSystem.ScheduleEvent(AudioEvent.CreateUIEvent(UIEventType.FocusZoomIn, UIAudioProfile.None, _cameraView.GetInterpolationSpeed()));
				}
				else
				{
					SetWorldGridVisible(visible: false);
					SetMotorwayGridVisible(visible: false);
					_tilemapView.viewMode = TilemapView.ViewMode.Normal;
					_cameraView.ResetPlayerViewport();
					_gameUI.SetDrawButtonsVisible(visible: false);
					if (_gameUI.CurrentRoadDrawMode == RoadDrawMode.Remove)
					{
						_gameUI.ToggleDrawMode();
					}
					_audioSystem.ScheduleEvent(AudioEvent.CreateUIEvent(UIEventType.FocusZoomOut, UIAudioProfile.None, _cameraView.GetInterpolationSpeed()));
				}
			}
			OnActionComplete();
		}
		else if (_inputState.TouchCount <= 1)
		{
			_cameraView.ReleasePlayerPan();
			OnActionComplete();
		}
	}

	public static TouchCameraAction Create(PlayerActionGroup owningGroup, IScope scope, float timestamp)
	{
		TouchCameraAction touchCameraAction = scope.Get<TouchCameraAction>();
		touchCameraAction.InitializeAction(owningGroup, timestamp);
		if (owningGroup.InstigatingInputEvent.Source == InputEventSource.Touch)
		{
			touchCameraAction.RegisterObserveInputEvent(InputEventFilter.CreateTouchEventFilter(0, InputEventButtonState.JustUp), ObserverGreediness.BlocksNewActions);
			touchCameraAction.RegisterObserveInputEvent(InputEventFilter.CreateTouchEventFilter(1, InputEventButtonState.JustUp), ObserverGreediness.BlocksNewActions);
		}
		touchCameraAction.OnActionBegin(timestamp);
		return touchCameraAction;
	}

	public override void Reset()
	{
		base.Reset();
		_isPanning = false;
		_isPinching = false;
		_initialPinchDistance = 0f;
		_initialPinchOrthoZoom = 0f;
		_initialScreenPosition = default(Vector2);
		_currentScreenPosition = default(Vector2);
		_panOriginCameraPosition = default(Vector2);
		_panOriginWorldPosition = default(Vector2);
	}
}
