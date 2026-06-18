import { Component, ViewChild, ElementRef, AfterViewChecked, OnInit, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

interface ChatMessage {
  role: 'user'|'assistant';
  content: string;
  sources?: string[];
  suggested_questions?: string[];
  suggested_question_ids?: number[];
  is_verified_static?: boolean;
}

@Component({
  selector: 'app-chat-interface',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-interface.component.html'
})
export class ChatInterfaceComponent implements OnInit, AfterViewChecked {
  @ViewChild('chatContainer') private chatContainer!: ElementRef;
  @Input() isEmbedded: boolean = false;
  
  question = '';
  
  defaultGreeting: ChatMessage = {role: 'assistant', content: 'வணக்கம்! நான் உங்கள் \'அறிக புறநானூறு\' AI தளம். புறநானூறு பற்றிய உங்கள் கேள்விகளை என்னிடம் கேட்கலாம்!'};
  messages: ChatMessage[] = [];
  
  starterQuestions: {id: number, question: string}[] = [];
  
  loading = false;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.loadChatHistory();
    if (this.messages.length === 1) {
      this.fetchStarterQuestions();
    }
  }

  fetchStarterQuestions() {
    this.api.getStarterQa().subscribe({
      next: (res) => {
        let starters: any[] = [];
        if (res && res.length > 0) {
          starters = res.map((r: any) => ({id: r.id, question: r.question}));
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
      {id: 0, question: "புறநானூறு என்றால் என்ன?"},
      {id: 0, question: "களம்புக என்றால் என்ன?"}
    ];
  }

  attachStarters(starters: any[]) {
    if (this.messages.length === 1) {
      this.messages[0].suggested_questions = starters.map(s => s.question);
      this.messages[0].suggested_question_ids = starters.map(s => s.id);
      this.saveChatHistory();
    }
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }
  
  loadChatHistory() {
    const saved = localStorage.getItem('sangam_chat_history');
    if (saved) {
      try {
        this.messages = JSON.parse(saved);
        // Force update the old greeting to the new one if it exists
        if (this.messages.length > 0 && this.messages[0].role === 'assistant') {
          if (this.messages[0].content.includes('Sangam AI assistant') || this.messages[0].content.includes('Vanakkam!')) {
            this.messages[0].content = this.defaultGreeting.content;
            this.saveChatHistory();
          }
        }
      } catch (e) {
        this.messages = [{ ...this.defaultGreeting }];
      }
    } else {
      this.messages = [{ ...this.defaultGreeting }];
    }
  }
  
  saveChatHistory() {
    localStorage.setItem('sangam_chat_history', JSON.stringify(this.messages));
  }
  
  newChat() {
    this.messages = [{ ...this.defaultGreeting }];
    this.saveChatHistory();
    this.fetchStarterQuestions();
  }

  scrollToBottom(): void {
    try {
      this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
    } catch(err) { }
  }
  
  sendQuestion(q: string, id?: number) {
    this.question = q;
    // Don't pass id if it's 0 (fallback)
    this.sendMessage(id && id > 0 ? id : undefined);
  }

  sendMessage(staticQuestionId?: number) {
    if (!this.question.trim() || this.loading) return;
    
    const userQ = this.question;
    this.messages.push({role: 'user', content: userQ});
    this.question = '';
    this.loading = true;
    this.saveChatHistory();

    if (staticQuestionId) {
      this.api.getQaAnswer(staticQuestionId).subscribe({
        next: (res) => {
          this.messages.push({
            role: 'assistant', 
            content: res.answer,
            suggested_questions: res.related_questions,
            suggested_question_ids: res.related_question_ids,
            is_verified_static: true
          });
          this.loading = false;
          this.saveChatHistory();
        },
        error: (err) => {
          console.error(err);
          // Fallback to normal AI chat if static fetch fails
          this.fetchAiResponse(userQ);
        }
      });
    } else {
      this.fetchAiResponse(userQ);
    }
  }

  fetchAiResponse(userQ: string) {
    let historyToSend = this.messages.slice(0, -1);
    if (historyToSend.length > 0 && historyToSend[0].content === this.defaultGreeting.content) {
      historyToSend = historyToSend.slice(1);
    }
    
    const formattedHistory = historyToSend.map(m => ({role: m.role, content: m.content}));

    this.api.chatWithAi(userQ, formattedHistory).subscribe({
      next: (res) => {
        this.messages.push({
          role: 'assistant', 
          content: res.answer,
          sources: res.context_sources,
          suggested_questions: res.suggested_questions,
          suggested_question_ids: res.suggested_question_ids,
          is_verified_static: res.is_verified_static
        });
        this.loading = false;
        this.saveChatHistory();
      },
      error: (err) => {
        console.error(err);
        this.messages.push({role: 'assistant', content: 'Sorry, an error occurred while fetching the answer.'});
        this.loading = false;
        this.saveChatHistory();
      }
    });
  }
}
