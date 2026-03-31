import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:video_player/video_player.dart';

class ChatBubble extends StatefulWidget {
  final String text;
  final bool isUser;
  final String? infoUrl;

  const ChatBubble({
    required this.text,
    required this.isUser,
    this.infoUrl,
    super.key,
  });

  @override
  State<ChatBubble> createState() => _ChatBubbleState();
}

class _ChatBubbleState extends State<ChatBubble>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _scaleAnimation;
  late Animation<Offset> _slideAnimation;
  late String _displayText;
  String? _videoUrl;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );

    _scaleAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(parent: _animController, curve: Curves.elasticOut),
    );

    _slideAnimation = Tween<Offset>(
      begin: widget.isUser ? const Offset(0.3, 0) : const Offset(-0.3, 0),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _animController, curve: Curves.easeOut));

    _extractVideoFromMessage();

    _animController.forward();
  }

  void _extractVideoFromMessage() {
    _displayText = widget.text;

    final labeled = RegExp(
      r'Video\s+gi[oớ]i\s+thi[eệ]u\s+ng[aà]nh\s*:\s*(https?://[^\s]+)',
      caseSensitive: false,
      unicode: true,
    );
    final labeledMatch = labeled.firstMatch(_displayText);
    if (labeledMatch != null) {
      _videoUrl = labeledMatch.group(1);
      _displayText = _displayText.replaceFirst(labeled, '').trim();
      return;
    }

    final mp4 = RegExp(r'(https?://[^\s]+\.mp4)', caseSensitive: false);
    final mp4Match = mp4.firstMatch(_displayText);
    if (mp4Match != null) {
      _videoUrl = mp4Match.group(1);
      _displayText = _displayText.replaceFirst(mp4, '').trim();
    }
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isMobile = width < 600;
    final isTablet = width >= 600 && width < 1024;
    final maxBubbleWidth = isMobile
        ? width * 0.78
        : isTablet
        ? width * 0.62
        : 760.0;

    final fg = widget.isUser ? Colors.white : const Color(0xFF001A33);
    final align = widget.isUser ? Alignment.centerRight : Alignment.centerLeft;
    final radius = BorderRadius.only(
      topLeft: const Radius.circular(16),
      topRight: const Radius.circular(16),
      bottomLeft: Radius.circular(widget.isUser ? 16 : 4),
      bottomRight: Radius.circular(widget.isUser ? 4 : 16),
    );

    return SlideTransition(
      position: _slideAnimation,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: Align(
          alignment: align,
          child: Container(
            constraints: BoxConstraints(maxWidth: maxBubbleWidth),
            margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              gradient: widget.isUser
                  ? const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFF004FC0), Color(0xFF0066FF)],
                    )
                  : LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Colors.grey[100]!, Colors.grey[200]!],
                    ),
              borderRadius: radius,
              boxShadow: [
                BoxShadow(
                  color: widget.isUser
                      ? const Color(0xFF004FC0).withValues(alpha: 0.2)
                      : Colors.grey.withValues(alpha: 0.1),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _displayText,
                  style: TextStyle(
                    color: fg,
                    fontSize: 14,
                    height: 1.4,
                    fontWeight: widget.isUser
                        ? FontWeight.w500
                        : FontWeight.normal,
                  ),
                ),
                if (!widget.isUser && _videoUrl != null) ...[
                  const SizedBox(height: 10),
                  _InlineVideoPlayer(url: _videoUrl!),
                ],
                if (widget.infoUrl != null && widget.infoUrl!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () async {
                        final Uri url = Uri.parse(widget.infoUrl!);
                        if (await canLaunchUrl(url)) {
                          await launchUrl(
                            url,
                            mode: LaunchMode.externalApplication,
                          );
                        }
                      },
                      icon: const Icon(Icons.open_in_new, size: 14),
                      label: const Text(
                        'Xem chi tiết tuyển sinh',
                        style: TextStyle(fontSize: 12),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF0066FF),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 6,
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _InlineVideoPlayer extends StatefulWidget {
  final String url;

  const _InlineVideoPlayer({required this.url});

  @override
  State<_InlineVideoPlayer> createState() => _InlineVideoPlayerState();
}

class _InlineVideoPlayerState extends State<_InlineVideoPlayer> {
  VideoPlayerController? _controller;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initPlayer();
  }

  Future<void> _initPlayer() async {
    try {
      final controller = VideoPlayerController.networkUrl(
        Uri.parse(widget.url),
      );
      await controller.initialize();
      controller.setLooping(false);
      if (!mounted) {
        controller.dispose();
        return;
      }
      setState(() {
        _controller = controller;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Không tải được video trong app.';
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  String _fmt(Duration d) {
    final mm = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final ss = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    final hh = d.inHours;
    return hh > 0 ? '${hh.toString().padLeft(2, '0')}:$mm:$ss' : '$mm:$ss';
  }

  Future<void> _openExternally() async {
    final uri = Uri.parse(widget.url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFFD3DDF5)),
        ),
        child: Row(
          children: [
            const Icon(Icons.videocam_off, size: 18, color: Color(0xFF8A5A00)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                _error!,
                style: const TextStyle(fontSize: 12, color: Color(0xFF5C5C5C)),
              ),
            ),
            TextButton(
              onPressed: _openExternally,
              child: const Text('Mở video'),
            ),
          ],
        ),
      );
    }

    final c = _controller;
    if (c == null || !c.value.isInitialized) {
      return Container(
        width: double.infinity,
        height: 180,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFFD3DDF5)),
        ),
        child: const Center(child: CircularProgressIndicator(strokeWidth: 2)),
      );
    }

    final aspect = c.value.aspectRatio > 0 ? c.value.aspectRatio : (16 / 9);
    final pos = c.value.position;
    final dur = c.value.duration;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFD3DDF5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: AspectRatio(aspectRatio: aspect, child: VideoPlayer(c)),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              IconButton(
                onPressed: () {
                  setState(() {
                    if (c.value.isPlaying) {
                      c.pause();
                    } else {
                      c.play();
                    }
                  });
                },
                icon: Icon(c.value.isPlaying ? Icons.pause : Icons.play_arrow),
                splashRadius: 18,
              ),
              Expanded(
                child: Slider(
                  value: dur.inMilliseconds > 0
                      ? (pos.inMilliseconds
                            .clamp(0, dur.inMilliseconds)
                            .toDouble())
                      : 0,
                  max: dur.inMilliseconds > 0
                      ? dur.inMilliseconds.toDouble()
                      : 1,
                  onChanged: (v) async {
                    await c.seekTo(Duration(milliseconds: v.toInt()));
                    setState(() {});
                  },
                ),
              ),
              const SizedBox(width: 4),
              Text(
                '${_fmt(pos)} / ${_fmt(dur)}',
                style: const TextStyle(fontSize: 11, color: Color(0xFF4D4D4D)),
              ),
              const SizedBox(width: 8),
              IconButton(
                onPressed: _openExternally,
                icon: const Icon(Icons.open_in_new, size: 18),
                splashRadius: 18,
                tooltip: 'Mở ngoài trình duyệt',
              ),
            ],
          ),
        ],
      ),
    );
  }
}
