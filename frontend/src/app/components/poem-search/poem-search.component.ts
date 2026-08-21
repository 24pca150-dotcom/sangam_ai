import { Component, OnInit } from '@angular/core';
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
export class PoemSearchComponent implements OnInit {
  searchQuery = '';
  results: any[] = [];
  loading = false;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.search();
  }

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

  getCleanText(poem: any): string {
    if (poem?.line_by_line_meaning?.length) {
      return poem.line_by_line_meaning.map((l: any) => l.split_line).join(' ');
    }
    return poem?.basic_information?.original_tamil_text || '';
  }
}
