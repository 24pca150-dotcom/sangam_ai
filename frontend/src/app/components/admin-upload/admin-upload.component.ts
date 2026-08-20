import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-admin-upload',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-upload.component.html'
})
export class AdminUploadComponent {
  selectedFile: File | null = null;
  fileContent: string = '';
  loading = false;
  message = '';
  isError = false;
  uploadMode: 'poem' | 'qa' = 'poem';

  constructor(private api: ApiService) {}

  setMode(mode: 'poem' | 'qa') {
    this.uploadMode = mode;
    this.selectedFile = null;
    this.fileContent = '';
    this.message = '';
  }

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0];
    if (this.selectedFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.fileContent = e.target?.result as string;
      };
      reader.readAsText(this.selectedFile);
    }
  }

  uploadData() {
    if (!this.fileContent) return;
    
    this.loading = true;
    this.message = '';
    
    try {
      let jsonData = JSON.parse(this.fileContent);
      let apiCall;

      if (this.uploadMode === 'poem') {
        // If user uploaded a single poem JSON object instead of an array, wrap it in array
        if (!Array.isArray(jsonData)) {
          jsonData = [jsonData];
        }
        apiCall = this.api.uploadDataset(jsonData);
      } else {
        // If user uploaded a raw array of QA pairs, wrap it in the expected { qa_pairs: [...] } format
        if (Array.isArray(jsonData)) {
          jsonData = { qa_pairs: jsonData };
        }
        apiCall = this.api.uploadQaDataset(jsonData);
      }

      apiCall.subscribe({
        next: (res) => {
          this.message = res.message || 'Data uploaded successfully!';
          this.isError = false;
          this.loading = false;
          this.selectedFile = null;
          this.fileContent = '';
        },
        error: (err) => {
          console.error(err);
          const detail = err.error?.detail ? (typeof err.error.detail === 'string' ? err.error.detail : JSON.stringify(err.error.detail)) : '';
          this.message = 'Failed to upload data. ' + detail;
          this.isError = true;
          this.loading = false;
        }
      });
    } catch (e) {
      this.message = 'Invalid JSON file.';
      this.isError = true;
      this.loading = false;
    }
  }

}
