import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/api_trip.dart';
import '../models/api_trip_stats.dart';

class TripHistoryPage extends StatefulWidget {
  final int userId;

  const TripHistoryPage({Key? key, required this.userId}) : super(key: key);

  @override
  TripHistoryPageState createState() => TripHistoryPageState();
}

class TripHistoryPageState extends State<TripHistoryPage> {
  int selectedFilter = 0;
  int selectedTab = 0;
  int chartRange = 1;

  final ApiService _api = ApiService();
  late Future<List<ApiTrip>> _futureTrips;
  late Future<TripStats> _futureStats;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    _futureTrips = _api.fetchTrips(widget.userId);
    _futureStats = _api.fetchTripStats(widget.userId);
  }

  void reloadData() {
    setState(() {
      _loadData();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          'Trip History',
          style: TextStyle(
            color: Color(0xFF4CAF50),
            fontSize: 30,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 16),
            child: Icon(Icons.calendar_today_rounded, color: Colors.grey),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: const Color(0xFFBDB8B8),
                borderRadius: BorderRadius.circular(30),
              ),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final tabWidth = (constraints.maxWidth - 8) / 2;
                  return Stack(
                    children: [
                      AnimatedPositioned(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.easeInOut,
                        left: selectedTab == 0 ? 4 : tabWidth + 4,
                        top: 4,
                        child: Container(
                          width: tabWidth - 4,
                          height: 42,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(30),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.08),
                                blurRadius: 4,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                        ),
                      ),
                      Row(
                        children: [
                          Expanded(
                            child: GestureDetector(
                              onTap: () => setState(() => selectedTab = 0),
                              child: Container(
                                height: 50,
                                alignment: Alignment.center,
                                child: Text(
                                  'Trip List',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w600,
                                    color: selectedTab == 0
                                        ? Colors.black
                                        : Colors.black,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          Expanded(
                            child: GestureDetector(
                              onTap: () => setState(() => selectedTab = 1),
                              child: Container(
                                height: 50,
                                alignment: Alignment.center,
                                child: Text(
                                  'Charts',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w600,
                                    color: selectedTab == 1
                                        ? Colors.black
                                        : Colors.black,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  );
                },
              ),
            ),

            const SizedBox(height: 14),

            // tab Trip List
            if (selectedTab == 0)
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildFilterButton('All Transport', 0),
                    _buildFilterButton('This Week', 1),
                    _buildFilterButton('This Month', 2),
                  ],
                ),
              ),
            if (selectedTab == 0) const SizedBox(height: 18),
            if (selectedTab == 1) const SizedBox(height: 18),


            FutureBuilder<List<ApiTrip>>(
              future: _futureTrips,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.only(top: 32.0),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }

                if (snapshot.hasError) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 32.0),
                    child: Text(
                      'Failed to load trips: ${snapshot.error}',
                      style: const TextStyle(color: Colors.red),
                    ),
                  );
                }

                final allTrips = snapshot.data ?? [];
                final filteredTrips = _applyFilter(allTrips);

                //TAB CHARTS
                if (selectedTab == 1) {
                  return FutureBuilder<TripStats>(
                    future: _futureStats,
                    builder: (context, snap) {
                      if (snap.connectionState == ConnectionState.waiting) {
                        return const Padding(
                          padding: EdgeInsets.only(top: 32.0),
                          child: Center(child: CircularProgressIndicator()),
                        );
                      }
                      if (snap.hasError || !snap.hasData) {
                        return Padding(
                          padding: const EdgeInsets.only(top: 32.0),
                          child: Text(
                            'Failed to load stats: ${snap.error}',
                            style: const TextStyle(color: Colors.red),
                          ),
                        );
                      }

                      final stats = snap.data!;
                      List<SeriesPoint> currentSeries;
                      if (chartRange == 0) {
                        currentSeries = stats.daily;
                      } else if (chartRange == 1) {
                        currentSeries = stats.weekly;
                      } else {
                        currentSeries = stats.monthly;
                      }

                      final values =
                      currentSeries.map((p) => p.credits.toDouble()).toList();
                      final labels = currentSeries.map((p) => p.label).toList();

                      final perfTitle = chartRange == 0
                          ? 'Daily Performance'
                          : chartRange == 1
                          ? 'Weekly Performance'
                          : 'Monthly Performance';

                      return Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              _buildChartRangeChip('Daily', 0),
                              const SizedBox(width: 6),
                              _buildChartRangeChip('Weekly', 1),
                              const SizedBox(width: 6),
                              _buildChartRangeChip('Monthly', 2),
                            ],
                          ),
                          const SizedBox(height: 10),


                          _PerformanceCard(
                            title: perfTitle,
                            values: values,
                            labels: labels,
                          ),

                          _CreditsTrendCard(values: values, labels: labels),
                          const SizedBox(height: 16),

                          Row(
                            children: [
                              Expanded(
                                child: _SummaryCard(
                                  title: 'Total Trips',
                                  value: stats.totalTrips.toString(),
                                  valueColor: const Color(0xFF4CAF50),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: _SummaryCard(
                                  title: 'Total Credits',
                                  value: stats.totalCredits.toString(),
                                  valueColor: const Color(0xFF30A0FB),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                        ],
                      );
                    },
                  );
                }

                // ======= TAB TRIP LIST =======
                if (filteredTrips.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.only(top: 24.0),
                    child: Text(
                      'No trips found for the selected filter.',
                      style: TextStyle(color: Colors.grey),
                    ),
                  );
                }

                return Column(
                  children: filteredTrips.map((t) {
                    return _TripCard(
                      date: _formatDate(t.date),
                      trips: t.transportModes.length, // số phương tiện = số trip
                      distance: '${t.distanceKm.toStringAsFixed(2)} km',
                      transport: t.transportModes.join(', '),
                      credits: t.credits,
                    );
                  }).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  // ----- Filter All / This Week / This Month -----
  List<ApiTrip> _applyFilter(List<ApiTrip> trips) {
    final now = DateTime.now();

    // 0 = All Transport
    if (selectedFilter == 0) {
      return trips;
    }

    DateTime? parse(String s) {
      try {
        return DateTime.parse(s);
      } catch (_) {
        return null;
      }
    }

    // 1 = This Week
    if (selectedFilter == 1) {
      final startOfWeek = DateTime(
        now.year,
        now.month,
        now.day - (now.weekday - 1),
      );
      final endOfWeek = startOfWeek.add(const Duration(days: 6));

      return trips.where((t) {
        final d = parse(t.date);
        if (d == null) return false;
        return !d.isBefore(startOfWeek) && !d.isAfter(endOfWeek);
      }).toList();
    }

    // 2 = This Month
    if (selectedFilter == 2) {
      return trips.where((t) {
        final d = parse(t.date);
        if (d == null) return false;
        return d.year == now.year && d.month == now.month;
      }).toList();
    }

    return trips;
  }

  Widget _buildFilterButton(String label, int index) {
    final isSelected = selectedFilter == index;
    return GestureDetector(
      onTap: () => setState(() => selectedFilter = index),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 6),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF4CAF50) : Colors.transparent,
          border: Border.all(
            color: isSelected ? const Color(0xFF4CAF50) : Colors.grey,
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? Colors.white : Colors.black87,
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ),
    );
  }

  // Chip chọn Daily / Weekly / Monthly cho Charts
  Widget _buildChartRangeChip(String label, int index) {
    final selected = chartRange == index;
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      selectedColor: const Color(0xFF4CAF50),
      labelStyle: TextStyle(
        color: selected ? Colors.white : Colors.black87,
      ),
      onSelected: (_) {
        setState(() {
          chartRange = index;
        });
      },
    );
  }
}

// ---------------- Helper & Widgets phụ ----------------

// format "2025-09-18" -> "Sep 18, 2025"
String _formatDate(String iso) {
  try {
    final d = DateTime.parse(iso);
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    final m = months[d.month - 1];
    return '$m ${d.day}, ${d.year}';
  } catch (_) {
    return iso;
  }
}

class _TripCard extends StatelessWidget {
  final String date;
  final int trips;
  final String distance;
  final String transport;
  final int credits;

  const _TripCard({
    required this.date,
    required this.trips,
    required this.distance,
    required this.transport,
    required this.credits,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Left
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        date,
                        style: const TextStyle(
                          color: Colors.black,
                          fontWeight: FontWeight.w500,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade200,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '$trips trip${trips > 1 ? 's' : ''}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Colors.black,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '$distance   -   $transport',
                    style: const TextStyle(
                      color: Colors.black,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            // Right
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '+$credits',
                  style: const TextStyle(
                    color: Color(0xFF4CAF50),
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Credits earned',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ----- Cards cho Charts -----

class _PerformanceCard extends StatelessWidget {
  final String title;
  final List<double> values;
  final List<String> labels;

  const _PerformanceCard({
    required this.title,
    required this.values,
    required this.labels,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: Colors.black,
              ),
            ),
            const SizedBox(height: 12),
            _MiniBarChart(values: values, labels: labels),
          ],
        ),
      ),
    );
  }
}


class _CreditsTrendCard extends StatelessWidget {
  final List<double> values;
  final List<String> labels;

  const _CreditsTrendCard({required this.values, required this.labels});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Credits Trend',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: Colors.black,
              ),
            ),
            const SizedBox(height: 12),
            _MiniLineChart(values: values, labels: labels),
          ],
        ),
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String title;
  final String value;
  final Color valueColor;

  const _SummaryCard({
    required this.title,
    required this.value,
    required this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
        child: Column(
          children: [
            Text(
              value,
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: valueColor,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: TextStyle(
                fontSize: 13,
                color: Colors.grey.shade700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ----- Bar chart: tăng bề ngang cột -----

class _MiniBarChart extends StatelessWidget {
  final List<double> values;
  final List<String> labels;

  const _MiniBarChart({required this.values, required this.labels});

  @override
  Widget build(BuildContext context) {
    if (values.isEmpty) {
      return const SizedBox(
        height: 80,
        child: Center(child: Text('No data')),
      );
    }

    final maxVal = values.reduce((a, b) => a > b ? a : b) * 1.2;

    return SizedBox(
      height: 140,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: List.generate(values.length, (i) {
          final h = (values[i] / maxVal) * 100;
          return Column(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              Container(
                height: h.clamp(6, 100),
                width:45, // tăng từ 18 -> 24 cho cột bự hơn
                decoration: BoxDecoration(
                  color: const Color(0xFF4CAF50),
                  borderRadius: BorderRadius.circular(5),
                ),
              ),
              const SizedBox(height: 6),
              Text(
                labels[i],
                style: TextStyle(
                  color: Colors.grey.shade600,
                  fontSize: 11,
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}

// ----- Line chart: label nằm phía dưới -----

class _MiniLineChart extends StatelessWidget {
  final List<double> values;
  final List<String> labels;

  const _MiniLineChart({required this.values, required this.labels});

  @override
  Widget build(BuildContext context) {
    if (values.isEmpty) {
      return const SizedBox(
        height: 100,
        child: Center(child: Text('No data')),
      );
    }

    return Column(
      children: [
        SizedBox(
          height: 110,
          width: double.infinity,
          child: CustomPaint(
            painter: _LineChartPainter(values),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: labels
              .map(
                (l) => Text(
              l,
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 11,
              ),
            ),
          )
              .toList(),
        ),
      ],
    );
  }
}

class _LineChartPainter extends CustomPainter {
  final List<double> values;

  _LineChartPainter(this.values);

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2) return;

    final paintLine = Paint()
      ..color = const Color(0xFF30A0FB)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final paintDot = Paint()
      ..color = const Color(0xFF30A0FB)
      ..style = PaintingStyle.fill;

    final maxVal = values.reduce((a, b) => a > b ? a : b) * 1.2;
    const minVal = 0.0;

    final dx = size.width / (values.length - 1);
    final chartHeight = size.height - 8; // chừa chút margin trên

    final path = Path();

    for (int i = 0; i < values.length; i++) {
      final x = dx * i;
      final normalized =
          (values[i] - minVal) / ((maxVal - minVal) == 0 ? 1 : (maxVal - minVal));
      final y = chartHeight - normalized * chartHeight;

      final point = Offset(x, y);
      if (i == 0) {
        path.moveTo(point.dx, point.dy);
      } else {
        path.lineTo(point.dx, point.dy);
      }

      canvas.drawCircle(point, 3, paintDot);
    }

    canvas.drawPath(path, paintLine);
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter oldDelegate) {
    return oldDelegate.values != values;
  }
}
