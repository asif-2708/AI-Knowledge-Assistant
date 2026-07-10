import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { environment } from '../../environments/environment';

export interface DocumentResponse {
  id: number;
  filename: string;
  uploaded_at: string;
}

@Injectable({ providedIn: 'root' })
export class DocumentService {
  private apiUrl = environment.apiUrl;
  private documentUpdate$ = new Subject<void>();

  constructor(private http: HttpClient) {}

  getDocuments(): Observable<DocumentResponse[]> {
    return this.http.get<DocumentResponse[]>(`${this.apiUrl}/documents/`);
  }

  deleteDocument(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/documents/${id}`);
  }

  notifyDocumentUpdate(): void {
    this.documentUpdate$.next();
  }

  onDocumentUpdate(): Observable<void> {
    return this.documentUpdate$.asObservable();
  }
}
