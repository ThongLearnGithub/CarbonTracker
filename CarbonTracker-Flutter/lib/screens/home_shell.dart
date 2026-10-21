import 'package:flutter/material.dart';
import 'home_page.dart';
import 'trip_history_page.dart';
import 'wallet_page.dart';
import 'settings_page.dart';
import 'my_voucher_page.dart';
import '../models/api_user.dart';

class HomeShell extends StatefulWidget {
  final User user;

  const HomeShell({super.key, required this.user});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;
  // GlobalKey để gọi reloadData() ở 2 page
  final GlobalKey<TripHistoryPageState> _historyKey =
    GlobalKey<TripHistoryPageState>();
  final GlobalKey<WalletPageState> _walletKey =
    GlobalKey<WalletPageState>();

  late final List<Widget> pages;

  @override
  void initState() {
    super.initState();
    pages = [
      // truyền thêm onTripSaved xuống HomePage
      HomePage(
        userId: widget.user.id,
        onTabSelected: (i) => setState(() => index = i),
        onTripSaved: _onTripSaved,
      ),
      TripHistoryPage(key: _historyKey, userId: widget.user.id),
      WalletPage(
        key: _walletKey,
        userId: widget.user.id,
        onTabSelected: (i) => setState(() => index = i),
      ),
      const MyVoucherPage(),
      SettingsPage(user: widget.user),
    ];
  }

  // Khi có trip mới thì reload History + Wallet
  void _onTripSaved() {
    _historyKey.currentState?.reloadData();
    _walletKey.currentState?.reloadData();
  }


  Widget _buildNavIcon(IconData icon, int i) {
    final bool isSelected = index == i;
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: isSelected ? const Color(0xFFC9F6C3) : Colors.transparent,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(
        icon,
        color: isSelected ? const Color(0xFF21A366) : Colors.grey,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWideScreen = constraints.maxWidth >= 850;
        final content = Expanded(child: pages[index]);

        if (isWideScreen) {
          return Scaffold(
            body: Row(
              children: [
                NavigationRail(
                  extended: true,
                  selectedIndex: index,
                  onDestinationSelected: (i) => setState(() => index = i),
                  backgroundColor: Colors.white,
                  indicatorColor: const Color(0xFFC9F6C3),
                  selectedLabelTextStyle: const TextStyle(
                    color: Color(0xFF21A366),
                    fontWeight: FontWeight.w600,
                  ),
                  unselectedLabelTextStyle:
                      const TextStyle(color: Colors.grey),
                  leading: const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Text(
                      'Carbon Tracker',
                      style: TextStyle(
                        color: Color(0xFF21A366),
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  destinations: const [
                    NavigationRailDestination(
                      icon: Icon(Icons.home_outlined),
                      selectedIcon: Icon(Icons.home),
                      label: Text('Home'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.history_outlined),
                      selectedIcon: Icon(Icons.history),
                      label: Text('History'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.account_balance_wallet_outlined),
                      selectedIcon: Icon(Icons.account_balance_wallet),
                      label: Text('Wallet'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.card_giftcard_outlined),
                      selectedIcon: Icon(Icons.card_giftcard),
                      label: Text('Voucher'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.settings_outlined),
                      selectedIcon: Icon(Icons.settings),
                      label: Text('Settings'),
                    ),
                  ],
                ),
                const VerticalDivider(width: 1),
                content,
              ],
            ),
          );
        }

        return Scaffold(
          body: pages[index],
          bottomNavigationBar: BottomNavigationBar(
            currentIndex: index,
            onTap: (i) => setState(() => index = i),
            type: BottomNavigationBarType.fixed,
            backgroundColor: Colors.white,
            selectedItemColor: const Color(0xFF21A366),
            unselectedItemColor: Colors.grey,
            showUnselectedLabels: true,
            items: [
              BottomNavigationBarItem(
                label: 'Home',
                icon: _buildNavIcon(Icons.home_outlined, 0),
              ),
              BottomNavigationBarItem(
                label: 'History',
                icon: _buildNavIcon(Icons.history_outlined, 1),
              ),
              BottomNavigationBarItem(
                label: 'Wallet',
                icon: _buildNavIcon(Icons.account_balance_wallet_outlined, 2),
              ),
              BottomNavigationBarItem(
                label: 'Voucher',
                icon: _buildNavIcon(Icons.card_giftcard_outlined, 3),
              ),
              BottomNavigationBarItem(
                label: 'Setting',
                icon: _buildNavIcon(Icons.settings_outlined, 4),
              ),
            ],
          ),
        );
      },
    );
  }
}

// class _StubPage extends StatelessWidget {
//   final String title;
//   const _StubPage({required this.title, super.key});
//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//         appBar: AppBar(title: Text(title)),
//         body: Center(
//             child: Text('$title page')
//         )
//     );
//   }
// }