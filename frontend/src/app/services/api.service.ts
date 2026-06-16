import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'https://sangam-ai.onrender.com/api';

  constructor(private http: HttpClient) { }

  searchPoems(keyword?: string, poet?: string, theme?: string): Observable<any> {
    let params: any = {};
    if (keyword) params.keyword = keyword;
    if (poet) params.poet = poet;
    if (theme) params.theme = theme;
    return this.http.get(`${this.baseUrl}/poems/search`, { params });
  }

  getPoem(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/poems/${id}`);
  }

  chatWithAi(question: string, chat_history: any[] = []): Observable<any> {
    return this.http.post(`${this.baseUrl}/chat`, { question, chat_history });
  }

  uploadDataset(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/poems/upload`, data);
  }

  uploadQaDataset(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/qa/upload`, data);
  }

  getStarterQa(): Observable<any> {
    return this.http.get(`${this.baseUrl}/qa/starter`);
  }

  getQaAnswer(questionId: number): Observable<any> {
    return this.http.get(`${this.baseUrl}/qa/${questionId}`);
  }
}
