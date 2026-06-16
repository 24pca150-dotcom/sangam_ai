import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-poem-search',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './poem-search.component.html'
})
export class PoemSearchComponent {
  searchQuery = '';
  results: any[] = [];
  loading = false;

  constructor(private api: ApiService) {}

  search() {
    this.loading = true;
    this.api.searchPoems(this.searchQuery).subscribe({
      next: (res) => {
        this.results = res;
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.loading = false;
      }
    });
  }
}
