import { Component, ViewChild, ElementRef, AfterViewChecked, OnInit, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  suggested_questions?: string[];
  suggested_question_ids?: number[];
  is_verified_static?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  messages: ChatMessage[];
}

@Component({
  selector: 'app-chat-interface',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-interface.component.html',
  styleUrls: ['./chat-interface.component.css']
})
export class ChatInterfaceComponent implements OnInit, AfterViewChecked {
  @ViewChild('chatContainer') private chatContainer!: ElementRef;
  @Input() isEmbedded: boolean = false;

  question = '';
  loading = false;
  isSidebarOpen: boolean = true;
  searchQuery: string = '';

  defaultGreeting: ChatMessage = {
    role: 'assistant',
    content: 'வணக்கம்! நான் உங்கள் \'அறிக புறநானூறு\' AI தளம். புறநானூறு பற்றிய உங்கள் கேள்விகளை என்னிடம் கேட்கலாம்!'
  };

  sessions: ChatSession[] = [];
  activeSessionId: string = '';

  constructor(private api: ApiService) {}

  ngOnInit() {
    if (this.isEmbedded || (typeof window !== 'undefined' && window.innerWidth < 768)) {
      this.isSidebarOpen = false;
    } else {
      this.isSidebarOpen = true;
    }
    this.loadSessions();
    if (this.messages.length === 1 && (!this.messages[0].suggested_questions || this.messages[0].suggested_questions.length === 0)) {
      this.fetchStarterQuestions();
    }
  }


  get activeSession(): ChatSession | undefined {
    return this.sessions.find(s => s.id === this.activeSessionId);
  }

  get messages(): ChatMessage[] {
    return this.activeSession?.messages || [];
  }

  get filteredSessions(): ChatSession[] {
    if (!this.searchQuery.trim()) {
      return this.sessions;
    }
    return this.sessions.filter(s =>
      s.title.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
      s.messages.some(m => m.content.toLowerCase().includes(this.searchQuery.toLowerCase()))
    );
  }

  loadSessions() {
    const savedSessions = localStorage.getItem('sangam_chat_sessions');
    const savedActiveId = localStorage.getItem('sangam_active_session_id');
    const isSameTabSession = typeof sessionStorage !== 'undefined' && sessionStorage.getItem('sangam_tab_active') === 'true';

    // Mark current browser tab session as active
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem('sangam_tab_active', 'true');
    }

    if (savedSessions) {
      try {
        this.sessions = JSON.parse(savedSessions);
      } catch (e) {
        this.sessions = [];
      }
    }

    // Migrate from legacy single chat history if sessions is empty
    if (this.sessions.length === 0) {
      const legacyHistory = localStorage.getItem('sangam_chat_history');
      if (legacyHistory) {
        try {
          const parsed = JSON.parse(legacyHistory);
          if (Array.isArray(parsed) && parsed.length > 0) {
            const firstUserMsg = parsed.find(m => m.role === 'user');
            const title = firstUserMsg ? this.truncateTitle(firstUserMsg.content) : 'பாடலின் ஒப்பீடு';
            const legacySession: ChatSession = {
              id: 'session_' + Date.now(),
              title,
              createdAt: Date.now(),
              messages: parsed
            };
            this.sessions.push(legacySession);
          }
        } catch (e) {}
      }
    }

    // Keep non-empty sessions with user questions
    this.sessions = this.sessions.filter(s => s.messages.some(m => m.role === 'user'));

    // Ensure valid greeting text in history sessions
    this.sessions.forEach(s => {
      if (s.messages.length > 0 && s.messages[0].role === 'assistant') {
        if (s.messages[0].content.includes('Sangam AI assistant') || s.messages[0].content.includes('Vanakkam!')) {
          s.messages[0].content = this.defaultGreeting.content;
        }
      }
    });

    // Page refresh in SAME tab -> Keep current active chat session!
    // Closing tab & re-opening fresh tab -> Start a fresh new chat session!
    if (isSameTabSession && savedActiveId && this.sessions.some(s => s.id === savedActiveId)) {
      this.activeSessionId = savedActiveId;
    } else {
      const freshSession: ChatSession = {
        id: 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
        title: 'புதிய உரையாடல்',
        createdAt: Date.now(),
        messages: [{ ...this.defaultGreeting }]
      };
      this.sessions.unshift(freshSession);
      this.activeSessionId = freshSession.id;
    }

    this.saveSessions();
  }



  saveSessions() {
    localStorage.setItem('sangam_chat_sessions', JSON.stringify(this.sessions));
    localStorage.setItem('sangam_active_session_id', this.activeSessionId);
  }

  newChat() {
    const newSession: ChatSession = {
      id: 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
      title: 'புதிய உரையாடல்',
      createdAt: Date.now(),
      messages: [{ ...this.defaultGreeting }]
    };
    this.sessions.unshift(newSession);
    this.activeSessionId = newSession.id;
    this.saveSessions();
    this.fetchStarterQuestions();
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      this.isSidebarOpen = false;
    }
  }

  selectSession(id: string) {
    this.activeSessionId = id;
    this.saveSessions();
    if (this.messages.length === 1 && (!this.messages[0].suggested_questions || this.messages[0].suggested_questions.length === 0)) {
      this.fetchStarterQuestions();
    }
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      this.isSidebarOpen = false;
    }
  }


  deleteSession(id: string, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    this.sessions = this.sessions.filter(s => s.id !== id);
    if (this.sessions.length === 0) {
      this.newChat();
    } else if (this.activeSessionId === id) {
      this.activeSessionId = this.sessions[0].id;
    }
    this.saveSessions();
  }

  clearAllSessions() {
    if (confirm('அனைத்து உரையாடல் வரலாற்றையும் நீக்க வேண்டுமா?')) {
      this.sessions = [];
      this.newChat();
    }
  }


  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }

  truncateTitle(text: string): string {
    const trimmed = text.trim();
    if (trimmed.length > 25) {
      return trimmed.substring(0, 25) + '...';
    }
    return trimmed;
  }

  fetchStarterQuestions() {
    this.api.getStarterQa().subscribe({
      next: (res) => {
        let starters: any[] = [];
        if (res && res.length > 0) {
          starters = res.map((r: any) => ({ id: r.id, question: r.question }));
        } else {
          starters = this.getFallbackStarters();
        }
        this.attachStarters(starters);
      },
      error: (err) => {
        console.error('Error fetching starter QA:', err);
        this.attachStarters(this.getFallbackStarters());
      }
    });
  }

  getFallbackStarters() {
    return [
      { id: 0, question: "புறநானூறு 88 ஆம் பாடலை இயற்றியவர் யார்?" },
      { id: 0, question: "இந்தப் பாடலில் புகழப்படும் மன்னன் யார்?" },
      { id: 0, question: "இந்தப் பாடலின் theme என்ன?" },
      { id: 0, question: "'களம்புகல்' என்பதன் பொருள் என்ன?" }
    ];
  }

  attachStarters(starters: any[]) {
    const session = this.activeSession;
    if (session && session.messages.length === 1) {
      session.messages[0].suggested_questions = starters.map(s => s.question);
      session.messages[0].suggested_question_ids = starters.map(s => s.id);
      this.saveSessions();
    }
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
    } catch (err) { }
  }

  sendQuestion(q: string, id?: number) {
    this.question = q;
    this.sendMessage(id && id > 0 ? id : undefined);
  }

  sendMessage(staticQuestionId?: number) {
    if (!this.question.trim() || this.loading) return;

    const session = this.activeSession;
    if (!session) return;

    const userQ = this.question;

    // Auto update title if session title is default or first question
    if (session.title === 'புதிய உரையாடல்' || session.messages.length <= 1) {
      session.title = this.truncateTitle(userQ);
    }

    session.messages.push({ role: 'user', content: userQ });
    this.question = '';
    this.loading = true;
    this.saveSessions();

    if (staticQuestionId) {
      this.api.getQaAnswer(staticQuestionId).subscribe({
        next: (res) => {
          session.messages.push({
            role: 'assistant',
            content: res.answer,
            suggested_questions: res.related_questions,
            suggested_question_ids: res.related_question_ids,
            is_verified_static: true
          });
          this.loading = false;
          this.saveSessions();
        },
        error: (err) => {
          console.error(err);
          this.fetchAiResponse(userQ);
        }
      });
    } else {
      this.fetchAiResponse(userQ);
    }
  }

  fetchAiResponse(userQ: string) {
    const session = this.activeSession;
    if (!session) return;

    let historyToSend = session.messages.slice(0, -1);
    if (historyToSend.length > 0 && historyToSend[0].content === this.defaultGreeting.content) {
      historyToSend = historyToSend.slice(1);
    }

    const formattedHistory = historyToSend.map(m => ({ role: m.role, content: m.content }));

    this.api.chatWithAi(userQ, formattedHistory).subscribe({
      next: (res) => {
        session.messages.push({
          role: 'assistant',
          content: res.answer,
          sources: res.context_sources,
          suggested_questions: res.suggested_questions,
          suggested_question_ids: res.suggested_question_ids,
          is_verified_static: res.is_verified_static
        });
        this.loading = false;
        this.saveSessions();
      },
      error: (err) => {
        console.error(err);
        session.messages.push({ role: 'assistant', content: 'மன்னித்துக்கொள்ளுங்கள், பதிலை பெறுவதில் பிழை ஏற்பட்டது.' });
        this.loading = false;
        this.saveSessions();
      }
    });
  }
}

