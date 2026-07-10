import { Component, ChangeDetectorRef } from '@angular/core';
import { UploadService } from '../services/upload.service';
import { DocumentService } from '../services/document.service';

@Component({
  selector: 'app-upload',
  standalone: false,
  templateUrl: './upload.component.html',
  styleUrls: ['./upload.component.css'],
})
export class UploadComponent {
  selectedFile?: File;
  message = '';
  isUploading = false;

  constructor(
    private uploadService: UploadService,
    private documentService: DocumentService,
    private cdr: ChangeDetectorRef
  ) {}

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile = input.files?.[0];
    this.message = '';
  }

  upload(): void {
    if (!this.selectedFile) {
      this.message = 'Select a document first.';
      return;
    }

    if (this.isUploading) {
      return;
    }

    this.isUploading = true;
    this.message = 'Indexing document... please wait.';
    this.cdr.detectChanges(); // Force UI to disable button and show spinner

    this.uploadService.uploadDocument(this.selectedFile).subscribe({
      next: () => {
        this.message = 'Upload succeeded.';
        this.isUploading = false;
        this.selectedFile = undefined;
        this.documentService.notifyDocumentUpdate();
        this.cdr.detectChanges();
      },
      error: (err) => {
        const errorMsg = err.error?.detail || 'Upload failed. Please try again.';
        this.message = errorMsg;
        this.isUploading = false;
        this.cdr.detectChanges();
      },
    });
  }
}
