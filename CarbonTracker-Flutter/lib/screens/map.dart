import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';
import 'package:flutter/foundation.dart';


class MapScreen extends StatefulWidget {
  const MapScreen({
    super.key,
    required this.userId,
    this.startTime,
    this.initialVehicle,
    this.onTripSaved,
  });

  final int userId;
  final DateTime? startTime;
  final String? initialVehicle;
  final VoidCallback? onTripSaved;

  @override
  State<MapScreen> createState() => _TrackingMapScreenState();
}

class _TrackingMapScreenState extends State<MapScreen> {
  GoogleMapController? _mapController;
  LatLng? _currentLatLng;
  StreamSubscription<Position>? _positionStream;
  Timer? _ticker;

  final Set<Polyline> _polylines = {};
  final List<LatLng> _route = [];
  final Set<Marker> _markers = {};
  final ApiService _api = ApiService();

  DateTime? _startTime;
  DateTime? _endTime;
  String? _vehicle;
  double _totalKm = 0.0;
  bool _lockedToUser = true;
  bool _isTracking = false;
  bool _isDemoMode = false;

  @override
  void initState() {
    super.initState();

    _vehicle = widget.initialVehicle;
    if (_vehicle != null) {
      _startTime = widget.startTime ?? DateTime.now();
      _isTracking = true;
    }

    _initLocation();

    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _positionStream?.cancel();
    _mapController?.dispose();
    _ticker?.cancel();
    super.dispose();
  }

  Future<void> _initLocation() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      await Geolocator.openLocationSettings();
      return;
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return;
    }

    if (permission == LocationPermission.deniedForever) return;

    try {
      final p = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 8),
      );
      _applyPosition(p, recenter: true, zoom: 16);
    } catch (e) {
      debugPrint('[Location] single fix failed: $e');
    }

    const settings = LocationSettings(
      accuracy: LocationAccuracy.bestForNavigation,
      distanceFilter: 5,
    );

    _positionStream =
        Geolocator.getPositionStream(locationSettings: settings).listen(
              (pos) {
            final goodEnough = pos.accuracy <= 40;
            _applyPosition(pos, recenter: _lockedToUser && goodEnough);
          },
          onError: (e) => debugPrint('[Location] stream error: $e'),
        );
  }

  Future<void> _applyPosition(
      Position pos, {
        bool recenter = false,
        double? zoom,
      }) async {
    final ll = LatLng(pos.latitude, pos.longitude);
    setState(() {
      _currentLatLng = ll;
      if (_isTracking) {
        _route.add(ll);
      }
      if (_isTracking && _route.length > 1) {
        _totalKm += _haversine(_route[_route.length - 2], _route.last);
      }

      if (_isTracking) {
        _polylines
          ..clear()
          ..add(
            Polyline(
              polylineId: const PolylineId('route'),
              points: List.of(_route),
              width: 4,
              color: Colors.blueAccent,
            ),
          );
      }

      _markers
        ..clear()
        ..add(
          Marker(
            markerId: const MarkerId('me'),
            position: ll,
            icon: BitmapDescriptor.defaultMarkerWithHue(
              BitmapDescriptor.hueAzure,
            ),
            infoWindow: InfoWindow(
              title: _vehicle ?? 'Moving',
              snippet: '${pos.accuracy.toStringAsFixed(0)} m',
            ),
          ),
        );
    });

    if (recenter && _mapController != null) {
      await _mapController!.animateCamera(
        CameraUpdate.newCameraPosition(
          CameraPosition(
            target: ll,
            zoom: zoom ?? 17,
            bearing: pos.heading,
          ),
        ),
      );
    }
  }

  double _haversine(LatLng a, LatLng b) {
    const R = 6371.0;
    final dLat = (b.latitude - a.latitude) * (pi / 180.0);
    final dLon = (b.longitude - a.longitude) * (pi / 180.0);
    final la1 = a.latitude * (pi / 180.0);
    final la2 = b.latitude * (pi / 180.0);
    final h = sin(dLat / 2) * sin(dLat / 2) +
        sin(dLon / 2) * sin(dLon / 2) * cos(la1) * cos(la2);
    return 2 * R * atan2(sqrt(h), sqrt(1 - h));
  }

  String _formattedTime() {
    if (_startTime == null) return '00:00';

    final end = _isTracking ? DateTime.now() : (_endTime ?? DateTime.now());
    final d = end.difference(_startTime!);

    final h = d.inHours;
    final m = d.inMinutes % 60;
    final s = d.inSeconds % 60;

    return h > 0
        ? '${h.toString().padLeft(2, '0')}:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}'
        : '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }


  Future<void> _recenterNow() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.best,
        timeLimit: const Duration(seconds: 8),
      );
      _lockedToUser = true;
      await _applyPosition(pos, recenter: true, zoom: 17);
    } catch (e) {
      debugPrint('[Location] recenter failed: $e');
    }
  }

  // Demo
  Future<void> _simulateDemoRoute() async {
    if (_currentLatLng == null) return;

    setState(() {
      _isDemoMode = true;
      _vehicle ??= 'Walking';
      if (!_isTracking) {
        _isTracking = true;
        _startTime = DateTime.now();
        _endTime = null;
        _totalKm = 0.0;
        _route.clear();
      }
    });

    final base = _currentLatLng!;

    final points = <LatLng>[
      base,
      LatLng(base.latitude + 0.0010, base.longitude),
      LatLng(base.latitude + 0.0020, base.longitude + 0.0010),
      LatLng(base.latitude + 0.0030, base.longitude + 0.0020),
      LatLng(base.latitude + 0.0040, base.longitude + 0.0030),
      LatLng(base.latitude + 0.0050, base.longitude + 0.0035),
      LatLng(base.latitude + 0.0060, base.longitude + 0.0030),
      LatLng(base.latitude + 0.0070, base.longitude + 0.0020),
      LatLng(base.latitude + 0.0080, base.longitude + 0.0010),
      LatLng(base.latitude + 0.0090, base.longitude),
    ];


    for (final p in points) {
      if (!mounted) break;

      // Tạo Position giả để tái dùng logic _applyPosition()
      final fake = Position(
        latitude: p.latitude,
        longitude: p.longitude,
        accuracy: 5,
        altitude: 0,
        heading: 0,
        speed: 1,
        speedAccuracy: 0,
        timestamp: DateTime.now(),
        altitudeAccuracy: 0,
        headingAccuracy: 0,
      );

      await _applyPosition(fake, recenter: true, zoom: 17);

      await Future.delayed(const Duration(seconds: 1));
    }

    setState(() {
      _isTracking = false;
      _endTime = DateTime.now();
    });
  }

  double _calculateCo2(String? vehicle, double distanceKm) {
    if (vehicle == 'Walking' || vehicle == 'Bicycle') {
      return 0.0;
    }

    final C02 = distanceKm * 0.5;
    return C02.clamp(0, 99).toDouble();
  }

  // Complete Trip
  void _showTripCompletedDialog(
      BuildContext context,
      int credits, {
        bool isDemo = false,
      }) {
    final totalTime = _formattedTime();
    final distance = _totalKm;
    final co2 = _calculateCo2(_vehicle, distance);


    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: Padding(
            padding: const EdgeInsets.all(18.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Align(
                  alignment: Alignment.topRight,
                  child: IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ),
                const Text(
                  'Trip Completed!',
                  style: TextStyle(
                    color: Colors.green,
                    fontWeight: FontWeight.bold,
                    fontSize: 22,
                  ),
                ),
                const SizedBox(height: 12),
                Container(
                  decoration: BoxDecoration(
                    color: Colors.green.shade100,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.directions_bus, color: Colors.green),
                      const SizedBox(width: 8),
                      Text(
                        _vehicle ?? 'Walking',
                        style: const TextStyle(
                          color: Colors.green,
                          fontWeight: FontWeight.w600,
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _TripInfoBox(
                      icon: Icons.access_time,
                      label: 'Total Time',
                      value: totalTime,
                    ),
                    _TripInfoBox(
                      icon: Icons.route,
                      label: 'Distance',
                      value: '${distance.toStringAsFixed(2)} km',
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                Container(
                  padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.eco, color: Colors.green),
                          SizedBox(width: 8),
                          Text(
                            'CO₂ Emitted',
                            style: TextStyle(color: Colors.black),
                          ),
                        ],
                      ),
                      Text(
                        '${co2.toStringAsFixed(2)} kg',
                        style: const TextStyle(
                          color: Colors.green,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 18),
                  decoration: BoxDecoration(
                    color: Colors.green,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Column(
                    children: [
                      const Icon(Icons.emoji_events,
                          color: Colors.white, size: 28),
                      const SizedBox(height: 6),
                      const Text(
                        'Carbon Credits Earned',
                        style: TextStyle(color: Colors.white),
                      ),
                      Text(
                        '+$credits',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 22,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 12,
                  runSpacing: 8,
                  children: [
                    OutlinedButton(
                      onPressed: () => Navigator.pop(context),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.black87,
                        side: const BorderSide(color: Colors.black26),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 30,
                          vertical: 10,
                        ),
                      ),
                      child: const Text('Close'),
                    ),
                    //  Done button
                    ElevatedButton(
                      onPressed: () {
                        Navigator.of(context).pop(); // close dialog

                        // DEMO: không callback reload
                        if (isDemo) {
                          Navigator.of(context).pop();
                          _isDemoMode = false;
                          return;
                        }

                        // REAL TRIP: thoát MapScreen + reload homepage
                        Navigator.of(context).pop();
                        widget.onTripSaved?.call();
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 30),
                      ),
                      child: const Text('Done'),
                    )

                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final startCamera = CameraPosition(
      target: _currentLatLng ?? const LatLng(10.762622, 106.660172),
      zoom: 15,
    );

    return Scaffold(
      body: _currentLatLng == null
          ? const Center(child: CircularProgressIndicator())
          : Stack(
        children: [
          GoogleMap(
            mapType: MapType.normal,
            initialCameraPosition: startCamera,
            myLocationEnabled: true,
            myLocationButtonEnabled: false,
            compassEnabled: true,
            zoomControlsEnabled: false,
            polylines: _polylines,
            markers: _markers,
            onMapCreated: (c) => _mapController = c,
            onCameraMoveStarted: () => _lockedToUser = false,
          ),
          Positioned(
            top: 60,
            left: 16,
            right: 16,
            child: _TrackingInfoCard(
              vehicle: _vehicle,
              timeText: _formattedTime(),
              distanceKm: _totalKm,
            ),
          ),
          if (_vehicle == null)
            Positioned(
              bottom: 100,
              left: 16,
              right: 16,
              child: _VehiclePicker(
                // ✅ Khi chọn vehicle lần đầu → bắt đầu đếm giờ
                onSelected: (v) {
                  setState(() {
                    _vehicle = v;
                    if (!_isTracking) {
                      _isTracking = true;
                      _startTime = DateTime.now();
                      _endTime = null;
                      _totalKm = 0.0;
                      _route.clear();
                      _polylines.clear();
                    }
                  });
                },
              ),
            ),
          Positioned(
            bottom: 30,
            left: 20,
            right: 20,
            child: ElevatedButton.icon(
              onPressed: () async {
                if (_vehicle == null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Please select a vehicle first.')),
                  );
                  return;
                }

                setState(() {
                  _isTracking = false;
                  _endTime = DateTime.now();
                  _positionStream?.cancel();
                });

                final distance = _totalKm;
                final credits = (distance * 1.5).round();

                // 🔥 Nếu đang DEMO → không gọi API, chỉ show dialog demo
                if (_isDemoMode) {
                  _showTripCompletedDialog(
                    context,
                    credits,
                    isDemo: true,
                  );
                  return;
                }

                // 👉 TRIP THẬT: lưu backend như cũ
                try {
                  await _api.createTrip(
                    userId: widget.userId,
                    distanceKm: distance,
                    transportModes: [_vehicle!],
                    credits: credits,
                  );

                  _showTripCompletedDialog(context, credits, isDemo: false);
                } catch (e) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Failed to save trip: $e')),
                  );
                }
              },

              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              icon: const Icon(Icons.stop, color: Colors.white),
              label: const Text(
                'Stop Trip',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ),
          ),
          Positioned(
            left: 16,
            bottom: 100,
            child: FloatingActionButton(
              mini: true,
              backgroundColor: Colors.white,
              shape: const CircleBorder(),
              onPressed: _recenterNow,
              child: const Icon(
                Icons.my_location,
                color: Color(0xFF4CAF50),
              ),
            ),
          ),
          if (kDebugMode) // chỉ hiện trong debug, build release sẽ ẩn
            Positioned(
              right: 16,
              bottom: 100,
              child: FloatingActionButton(
                mini: true,
                backgroundColor: Colors.white,
                shape: const CircleBorder(),
                onPressed: _simulateDemoRoute,
                child: const Icon(
                  Icons.play_arrow,
                  color: Colors.red,
                ),
              ),
            ),

        ],
      ),
    );
  }
}

/// ======= Widgets nhỏ =======

class _TrackingInfoCard extends StatelessWidget {
  const _TrackingInfoCard({
    required this.vehicle,
    required this.timeText,
    required this.distanceKm,
  });

  final String? vehicle;
  final String timeText;
  final double distanceKm;

  @override
  Widget build(BuildContext context) {
    final icon = _iconFor(vehicle);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
        child: Column(
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.green.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    'Tracking Active',
                    style: TextStyle(
                      color: Colors.green,
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                    ),
                  ),
                ),
                const Spacer(),
                if (icon != null) Icon(icon, color: Colors.green, size: 18),
                const SizedBox(width: 6),
                Flexible(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Text(
                      vehicle ?? 'Select Vehicle',
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        color: Colors.black87,
                      ),
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 8),

            // ==== NEW: Distance xuống dòng ====
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.access_time, size: 18),
                    const SizedBox(width: 6),
                    Text(
                      'Time: $timeText',
                      style: const TextStyle(color: Colors.black),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.route, size: 18),
                    const SizedBox(width: 6),
                    Text(
                      'Distance: ${distanceKm.toStringAsFixed(2)} km',
                      style: const TextStyle(color: Colors.black),
                    ),
                  ],
                ),
              ],
            )
          ],
        )
    );
  }

  IconData? _iconFor(String? v) {
    switch (v) {
      case 'E-Bus':
        return Icons.directions_bus;
      case 'Bus':
        return Icons.directions_bus;
      case 'E-Motorbike':
        return Icons.electric_moped;
      case 'Motorbike':
        return Icons.two_wheeler;
      case 'Car':
        return Icons.directions_car;
      case 'E-Car':
        return Icons.electric_car;
      case 'Bicycle':
        return Icons.directions_bike;
      case 'Walking':
        return Icons.directions_walk;
      default:
        return null;
    }
  }
}

class _TripInfoBox extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _TripInfoBox({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 120,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        children: [
          Icon(icon, color: Colors.black54),
          const SizedBox(height: 6),
          Text(
            label,
            style: const TextStyle(fontSize: 14, color: Colors.black),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
              color: Colors.black,
            ),
          ),
        ],
      ),
    );
  }
}

class _VehiclePicker extends StatefulWidget {
  const _VehiclePicker({required this.onSelected});

  final ValueChanged<String> onSelected;

  @override
  State<_VehiclePicker> createState() => _VehiclePickerState();
}

class _VehiclePickerState extends State<_VehiclePicker> {
  String? _selected;

  static const options = <String>[
    'E-Bus',
    'Bus',
    'E-Motorbike',
    'Motorbike',
    'Car',
    'E-Car',
    'Bicycle',
    'Walking',
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 8,
          ),
        ],
      ),
      child: Column(
        children: [
          const Text(
            'Select Vehicle',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: options.map((type) {
              return ChoiceChip(
                label: Text(type),
                selected: _selected == type,
                onSelected: (sel) {
                  setState(() => _selected = sel ? type : null);
                  if (sel) widget.onSelected(type);
                },
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
