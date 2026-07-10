import { Component, OnDestroy, OnInit, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { DocumentService, DocumentResponse } from '../services/document.service';

@Component({
  selector: 'app-documents',
  standalone: false,
  templateUrl: './documents.component.html',
  styleUrls: ['./documents.component.css'],
})
export class DocumentsComponent implements OnInit, OnDestroy {
  documents: DocumentResponse[] = [];
  isLoading = false;
  error = '';
  private subscriptions = new Subscription();

  constructor(
    private documentService: DocumentService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadDocuments();
    this.subscriptions.add(
      this.documentService.onDocumentUpdate().subscribe(() => {
        console.log('Document update notification received, reloading...');
        this.loadDocuments();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  loadDocuments(): void {
    console.log('loadDocuments() started');
    this.isLoading = true;
    this.error = '';
    this.cdr.detectChanges();

    this.documentService.getDocuments().subscribe({
      next: (data) => {
        console.log('loadDocuments() next callback with data:', data);
        this.documents = (data || []).map(doc => ({
          ...doc,
          uploaded_at: doc.uploaded_at ? doc.uploaded_at.replace(' ', 'T') : doc.uploaded_at
        }));
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('loadDocuments() error callback:', err);
        this.error = 'Failed to load documents.';
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  deleteDocument(id: number): void {
    if (confirm('Are you sure you want to delete this document? This will remove all its indexed chunks.')) {
      this.documentService.deleteDocument(id).subscribe({
        next: () => {
          this.loadDocuments();
        },
        error: (err) => {
          console.error('Failed to delete document:', err);
          this.error = 'Failed to delete the document.';
          this.cdr.detectChanges();
        },
      });
    }
  }
}

