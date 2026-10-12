import unittest
from printed_page_mapping import page_fields, SOURCE_HASH

class MappingTests(unittest.TestCase):
    def map(self):
        return {'source_sha256':SOURCE_HASH,'pdf_page_count':728,'pages':{
            '18':{'book_page':None},'19':{'book_page':4},'20':{'book_page':5},
            '323':{'book_page':308}}}

    def row(self,start,end):
        return {'source_sha256':SOURCE_HASH,'pdf_page_start':start,'pdf_page_end':end}

    def test_single_page(self):
        result=page_fields(self.row(323,323),self.map())
        self.assertEqual(result['book_pages'],'308')
        self.assertEqual(result['book_page_mapping_status'],'complete')

    def test_cross_page(self):
        result=page_fields(self.row(19,20),self.map())
        self.assertEqual(result['book_pages'],'4,5')
        self.assertEqual(result['book_page_start'],'4')
        self.assertEqual(result['book_page_end'],'5')

    def test_unprinted_chapter_page_no_inferred_number(self):
        result=page_fields(self.row(18,18),self.map())
        self.assertEqual(result['book_pages'],'')
        self.assertEqual(result['book_page_mapping_status'],'pdf_only')

    def test_partial_range_does_not_shrink_citation(self):
        result=page_fields(self.row(18,19),self.map())
        self.assertEqual(result['book_pages'],'4')
        self.assertEqual(result['book_page_start'],'')
        self.assertEqual(result['book_page_mapping_status'],'partial')

    def test_other_source_rejected(self):
        row=self.row(323,323);row['source_sha256']='another-book'
        with self.assertRaises(ValueError): page_fields(row,self.map())

    def test_invalid_pdf_range_rejected(self):
        with self.assertRaises(ValueError): page_fields(self.row(20,19),self.map())

if __name__=='__main__': unittest.main()
