import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PoemSearchComponent } from './poem-search.component';

describe('PoemSearchComponent', () => {
  let component: PoemSearchComponent;
  let fixture: ComponentFixture<PoemSearchComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoemSearchComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PoemSearchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
