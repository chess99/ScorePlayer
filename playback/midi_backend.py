import sys
import threading

try:
    import rtmidi
    # 定义MidiOut别名以避免linter警告 (如果rtmidi.MidiOut确实存在)
    if hasattr(rtmidi, 'MidiOut'):
        RtMidiOut = rtmidi.MidiOut
    else:
        # 旧版本rtmidi可能使用不同的名称
        RtMidiOut = getattr(rtmidi, 'RtMidiOut', None)
        if RtMidiOut is None:
            print("Error: Could not find MidiOut class in rtmidi module.", file=sys.stderr)
            sys.exit(1)
except ImportError:
    print("Error: rtmidi library not found.", file=sys.stderr)
    print("Please install it using: pip install python-rtmidi", file=sys.stderr)
    sys.exit(1)

try:
    from music21 import pitch
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

from playback.base import PlaybackBackend


class MidiPlaybackBackend(PlaybackBackend):
    """用MIDI设备播放音符的后端，提供精确的音符持续时间控制"""

    def __init__(self, port_name=None):
        """初始化MIDI后端
        
        Args:
            port_name: 特定MIDI设备名称，如果为None则使用第一个可用端口
                      如果没有可用端口，则创建虚拟端口
        """
        self.midi_out = RtMidiOut()
        self.port_name = port_name
        self.is_initialized = False
        
        # 跟踪当前活跃的音符
        self.active_notes = {}  # 键：pitch.nameWithOctave，值：{'midi_note': int, 'timer': Timer}
        
        # 打印可用MIDI端口作为参考
        available_ports = self.midi_out.get_ports()
        if available_ports:
            print(f"可用MIDI端口: {available_ports}")
        else:
            print("未找到MIDI设备，将创建虚拟MIDI端口")
        
        print("MidiPlaybackBackend创建完成。使用start()初始化MIDI连接。")

    def start(self):
        """初始化MIDI连接"""
        if self.is_initialized:
            return
            
        try:
            # 尝试打开特定端口或第一个可用端口
            available_ports = self.midi_out.get_ports()
            
            if self.port_name:
                # 尝试找到指定名称的端口
                for i, port in enumerate(available_ports):
                    if self.port_name.lower() in port.lower():
                        self.midi_out.open_port(i)
                        print(f"已连接到MIDI端口: {port}")
                        break
                else:
                    # 没找到指定端口，创建虚拟端口
                    print(f"未找到名为 '{self.port_name}' 的MIDI端口，创建虚拟端口")
                    self.midi_out.open_virtual_port(f"Piano Player - {self.port_name}")
            elif available_ports:
                # 使用第一个可用端口
                self.midi_out.open_port(0)
                print(f"已连接到MIDI端口: {available_ports[0]}")
            else:
                # 没有可用端口，创建虚拟端口
                self.midi_out.open_virtual_port("Piano Player")
                print("已创建虚拟MIDI端口: Piano Player")
                
            self.is_initialized = True
            
        except Exception as e:
            print(f"初始化MIDI连接时出错: {e}", file=sys.stderr)
            print("MIDI播放可能失败。", file=sys.stderr)
            
    def stop(self):
        """停止所有音符并关闭MIDI连接"""
        if not self.is_initialized:
            return
            
        try:
            # 发送所有音符的note-off消息
            for note_id, note_info in list(self.active_notes.items()):
                midi_note = note_info['midi_note']
                self._send_note_off(note_id, midi_note)
                # 取消所有定时器
                if 'timer' in note_info and note_info['timer'] is not None:
                    note_info['timer'].cancel()
                    
            # 清空活跃音符字典
            self.active_notes.clear()
            
            # 发送全部音符关闭消息 (MIDI CC 123)
            self.midi_out.send_message([0xB0, 123, 0])
            
            # 关闭MIDI连接
            self.midi_out.close_port()
            print("MIDI连接已关闭")
            self.is_initialized = False
            
        except Exception as e:
            print(f"关闭MIDI连接时出错: {e}", file=sys.stderr)

    def play_note(self, note_pitch: pitch.Pitch, duration_sec: float, apply_octave_shift: bool, volume: float, is_tie_continuation: bool = False):
        """播放单个音符
        
        Args:
            note_pitch: music21音高对象
            duration_sec: 持续时间（秒）
            apply_octave_shift: 是否应用八度移位（MIDI后端支持完整MIDI范围，通常不需要）
            volume: 音量 (0.0 到 1.0)
            is_tie_continuation: 是否是连音符的延续部分（MIDI后端会自动延长音符，无需重触发）
        """
        if not self.is_initialized:
            print("警告: MIDI后端未初始化，无法播放音符。", file=sys.stderr)
            return
            
        # 获取MIDI音符编号
        midi_note = note_pitch.midi
        note_id = note_pitch.nameWithOctave
        
        # 对于tie续音，MIDI最大的优势是可以自然延长前一个音符而不重触发
        # 检查该音符是否已在播放
        if is_tie_continuation and note_id in self.active_notes:
            # 取消之前设置的note-off定时器
            if 'timer' in self.active_notes[note_id] and self.active_notes[note_id]['timer'] is not None:
                self.active_notes[note_id]['timer'].cancel()
            
            # 创建新的定时器，继续播放相同时长
            timer = threading.Timer(duration_sec, self._send_note_off, args=[note_id, midi_note])
            timer.daemon = True
            timer.start()
            
            # 更新活跃音符信息
            self.active_notes[note_id]['timer'] = timer
            print(f"MIDI延长音符: {note_id} (延长 {duration_sec:.2f}秒)")
            return
            
        # 如果有octave shift，应用它（通常MIDI不需要，但保留此功能以兼容接口）
        if apply_octave_shift and hasattr(note_pitch, 'transpose'):
            # 计算偏移量（如果有）
            # 此处无实际操作，因为MIDI支持全范围
            pass
            
        # 计算速度值（音量），MIDI范围是0-127
        velocity = int(volume * 127)
        
        # 如果此音符已在播放，先停止它
        if note_id in self.active_notes:
            # 取消现有的定时器
            if 'timer' in self.active_notes[note_id] and self.active_notes[note_id]['timer'] is not None:
                self.active_notes[note_id]['timer'].cancel()
                
            # 发送note-off（不总是必要的，但为安全起见）
            self._send_note_off(note_id, self.active_notes[note_id]['midi_note'])
        
        # 发送note-on消息
        self.midi_out.send_message([0x90, midi_note, velocity])  # Channel 1 note-on
        print(f"MIDI播放音符: {note_id} (MIDI: {midi_note}, 音量: {velocity})")
        
        # 设置定时器，在适当时间发送note-off
        timer = threading.Timer(duration_sec, self._send_note_off, args=[note_id, midi_note])
        timer.daemon = True
        timer.start()
        
        # 记录活跃音符
        self.active_notes[note_id] = {
            'midi_note': midi_note,
            'timer': timer
        }

    def play_chord(self, chord_pitches: list[pitch.Pitch], duration_sec: float, apply_octave_shift: bool, volume: float, tied_pitches: list[pitch.Pitch] = None):
        """播放和弦（多个音符同时）
        
        Args:
            chord_pitches: 和弦中音高对象的列表
            duration_sec: 持续时间（秒）
            apply_octave_shift: 是否应用八度移位
            volume: 音量 (0.0 到 1.0)
            tied_pitches: 从前一个音符/和弦延续的音符列表
        """
        if not self.is_initialized:
            print("警告: MIDI后端未初始化，无法播放和弦。", file=sys.stderr)
            return
        
        # 创建tied音符集合，用于快速查找
        tied_note_names = set()
        if tied_pitches:
            tied_note_names = {p.nameWithOctave for p in tied_pitches}
            
        # 计算速度值（音量）
        velocity = int(volume * 127)
        
        # 记录和弦中的音符ID
        chord_note_ids = []
        tied_notes = []
        new_notes = []
        
        # 遍历和弦中的每个音符
        for p in chord_pitches:
            note_id = p.nameWithOctave
            chord_note_ids.append(note_id)
            midi_note = p.midi
            
            # 检查是否是tie续音
            if note_id in tied_note_names:
                tied_notes.append(note_id)
                
                # 延长已有音符的定时器
                if note_id in self.active_notes:
                    # 取消现有的定时器
                    if 'timer' in self.active_notes[note_id] and self.active_notes[note_id]['timer'] is not None:
                        self.active_notes[note_id]['timer'].cancel()
                    
                    # 创建新的定时器
                    timer = threading.Timer(duration_sec, self._send_note_off, args=[note_id, midi_note])
                    timer.daemon = True
                    timer.start()
                    
                    # 更新活跃音符信息
                    self.active_notes[note_id]['timer'] = timer
                    
                continue  # 跳过新音符的触发
            
            # 以下是非tie音符的处理
            new_notes.append(note_id)
            
            # 如果此音符已在播放，先停止它
            if note_id in self.active_notes:
                # 取消现有的定时器
                if 'timer' in self.active_notes[note_id] and self.active_notes[note_id]['timer'] is not None:
                    self.active_notes[note_id]['timer'].cancel()
                
                # 发送note-off（不总是必要的，但为安全起见）
                self._send_note_off(note_id, self.active_notes[note_id]['midi_note'])
            
            # 发送note-on消息
            self.midi_out.send_message([0x90, midi_note, velocity])  # Channel 1 note-on
            
            # 设置定时器
            timer = threading.Timer(duration_sec, self._send_note_off, args=[note_id, midi_note])
            timer.daemon = True
            timer.start()
            
            # 记录活跃音符
            self.active_notes[note_id] = {
                'midi_note': midi_note,
                'timer': timer
            }
        
        # 打印和弦信息
        if new_notes:
            print(f"MIDI播放和弦: {' | '.join(new_notes)}")
        if tied_notes:
            print(f"MIDI延长和弦音符: {' | '.join(tied_notes)}")
        if not new_notes and not tied_notes:
            print("MIDI和弦: 无有效音符")

    def rest(self, duration_sec: float):
        """暂停指定时间（休止符）"""
        # 休止符不需要发送MIDI消息，只需等待
        print(f"MIDI休止符: {duration_sec:.3f}秒")
        
    def _send_note_off(self, note_id: str, midi_note: int):
        """发送note-off消息并清理活跃音符记录"""
        try:
            # 发送note-off消息
            self.midi_out.send_message([0x80, midi_note, 0])  # Channel 1 note-off
            
            # 从活跃音符中删除
            if note_id in self.active_notes:
                del self.active_notes[note_id]
                
        except Exception as e:
            print(f"发送MIDI Note-Off消息时出错: {e}", file=sys.stderr) 