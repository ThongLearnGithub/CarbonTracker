import 'package:flutter/material.dart';
import 'voucher_detail_page.dart';

enum VoucherStatus { pending, used, expired }

class Voucher {
  final String title;
  final String description;
  final String? extraInfo;
  final IconData icon;
  final VoucherStatus status;
  final String code;
  final int credits;

  Voucher({
    required this.title,
    required this.description,
    this.extraInfo,
    required this.icon,
    required this.status,
    required this.code,
    required this.credits,
  });


  Voucher copyWith({VoucherStatus? status}) {
    return Voucher(
      title: title,
      description: description,
      extraInfo: extraInfo,
      icon: icon,
      status: status ?? this.status,
      code: code,
      credits: credits,
    );
  }
}

final List<Voucher> myVoucherStore = [
];

class MyVoucherPage extends StatefulWidget {
  const MyVoucherPage({super.key});

  @override
  State<MyVoucherPage> createState() => _MyVoucherPageState();
}

class _MyVoucherPageState extends State<MyVoucherPage> {
  VoucherStatus? _currentFilter;

  List<Voucher> get _allVouchers => myVoucherStore;

  @override
  Widget build(BuildContext context) {
    final pendingCount =
        _allVouchers.where((v) => v.status == VoucherStatus.pending).length;
    final usedCount =
        _allVouchers.where((v) => v.status == VoucherStatus.used).length;
    final expiredCount =
        _allVouchers.where((v) => v.status == VoucherStatus.expired).length;

    final filteredVouchers = _currentFilter == null
        ? _allVouchers
        : _allVouchers.where((v) => v.status == _currentFilter).toList();

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        elevation: 0,
        backgroundColor: Colors.white,
        centerTitle: false,
        title: const Text(
          'My Voucher',
          style: TextStyle(
            color: Color(0xFF4CAF50),
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 16),
            child: Icon(
              Icons.card_giftcard_outlined,
              color: Colors.grey,
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Row(
              children: [
                Expanded(
                  child: _SummaryCard(
                    label: 'Pending',
                    count: pendingCount,
                    color: const Color(0xFF30A0FB),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    label: 'Used',
                    count: usedCount,
                    color: const Color(0xFF4CAF50),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    label: 'Expired',
                    count: expiredCount,
                    color: const Color(0xFFBDB8B8),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 12),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: const Color(0xFFE0E0E0),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: [
                  _FilterChipButton(
                    label: 'All',
                    selected: _currentFilter == null,
                    onTap: () {
                      setState(() {
                        _currentFilter = null;
                      });
                    },
                  ),
                  _FilterChipButton(
                    label: 'Pending',
                    selected: _currentFilter == VoucherStatus.pending,
                    onTap: () {
                      setState(() {
                        _currentFilter = VoucherStatus.pending;
                      });
                    },
                  ),
                  _FilterChipButton(
                    label: 'Used',
                    selected: _currentFilter == VoucherStatus.used,
                    onTap: () {
                      setState(() {
                        _currentFilter = VoucherStatus.used;
                      });
                    },
                  ),
                  _FilterChipButton(
                    label: 'Expired',
                    selected: _currentFilter == VoucherStatus.expired,
                    onTap: () {
                      setState(() {
                        _currentFilter = VoucherStatus.expired;
                      });
                    },
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),


          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                for (final v in filteredVouchers) ...[
                  _VoucherCard(
                    voucher: v,
                    onTap: () async {
                      final result = await Navigator.of(context).push<VoucherStatus>(
                        MaterialPageRoute(
                          builder: (_) => VoucherDetailPage(voucher: v),
                        ),
                      );

                      // Nếu detail trả về "used" thì update trạng thái
                      if (result == VoucherStatus.used) {
                        setState(() {
                          final idx = _allVouchers.indexWhere((x) => x.code == v.code);
                          if (idx != -1) {
                            _allVouchers[idx] = _allVouchers[idx].copyWith(
                              status: VoucherStatus.used,
                            );
                          }
                        });
                      }
                    },
                  ),
                  const SizedBox(height: 12),
                ],
                _QuickTipBox(
                  message:
                  '💡 Quick tip\nTap on any voucher to view its code and use it at participating locations',
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String label;
  final int count;
  final Color color;

  const _SummaryCard({
    required this.label,
    required this.count,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.6)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '$count',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 18,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: color.withOpacity(0.9),
            ),
          ),
        ],
      ),
    );
  }
}


class _FilterChipButton extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChipButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bg = selected ? Colors.white : Colors.transparent;
    final textColor = selected ? Colors.black : Colors.black54;

    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          height: 32,
          margin: const EdgeInsets.symmetric(horizontal: 2),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(16),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
              color: textColor,
            ),
          ),
        ),
      ),
    );
  }
}

class _VoucherCard extends StatelessWidget {
  final Voucher voucher;
  final VoidCallback onTap;

  const _VoucherCard({
    required this.voucher,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final statusText = _statusLabel(voucher.status);
    final statusColor = _statusColor(voucher.status);
    final gradientColors = [
      const Color(0xFFE8F5E9),
      const Color(0xFFE0F7FA),
    ];

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: gradientColors,
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.8),
                shape: BoxShape.circle,
              ),
              child: Icon(
                voucher.icon,
                color: const Color(0xFF4CAF50),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          voucher.title,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.black87,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: statusColor.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          statusText,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: statusColor,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    voucher.description,
                    style: const TextStyle(
                      fontSize: 13,
                      color: Colors.black54,
                    ),
                  ),
                  const SizedBox(height: 6),
                  if (voucher.extraInfo != null)
                    Row(
                      children: [
                        const Icon(Icons.access_time,
                            size: 14, color: Colors.black45),
                        const SizedBox(width: 4),
                        Text(
                          voucher.extraInfo!,
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.black54,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _statusLabel(VoucherStatus status) {
    switch (status) {
      case VoucherStatus.pending:
        return 'Pending';
      case VoucherStatus.used:
        return 'Used';
      case VoucherStatus.expired:
        return 'Expired';
    }
  }

  Color _statusColor(VoucherStatus status) {
    switch (status) {
      case VoucherStatus.pending:
        return const Color(0xFF42A5F5);
      case VoucherStatus.used:
        return const Color(0xFF66BB6A);
      case VoucherStatus.expired:
        return Colors.grey;
    }
  }
}

class _QuickTipBox extends StatelessWidget {
  final String message;

  const _QuickTipBox({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFFC9F6C3),
        borderRadius: BorderRadius.circular(12),
      ),
      padding: const EdgeInsets.all(12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline, color: Color(0xFF4CAF50)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                fontSize: 13,
                color: Color(0xFF4CAF50),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
