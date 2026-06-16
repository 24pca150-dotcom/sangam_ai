import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-poem-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './poem-detail.component.html'
})
export class PoemDetailComponent implements OnInit {
  poem: any = null;
  loading = true;

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.api.getPoem(id).subscribe({
        next: (res) => {
          this.poem = res;
          this.loading = false;
        },
        error: (err) => {
          console.error(err);
          this.loading = false;
        }
      });
    }
  }
}
