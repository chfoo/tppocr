.PHONY: all pkmngb

all: pkmngb

pkmngb:
	text2image --text=training_text.txt \
		--outputbase=pkmngb_en.pkmn_gb_en_tppocr.exp0 \
		--font='pkmn_gb_en_tppocr Medium' --fonts_dir=../pkmngb_en_font/
	tesseract pkmngb_en.pkmn_gb_en_tppocr.exp0.tif pkmngb_en.pkmn_gb_en_tppocr.exp0 box.train.stderr
	unicharset_extractor pkmngb_en.pkmn_gb_en_tppocr.exp0.box
	mftraining -F font_properties -U unicharset -O pkmngb_en.unicharset pkmngb_en.pkmn_gb_en_tppocr.exp0.tr
	cntraining pkmngb_en.pkmn_gb_en_tppocr.exp0.tr
	wordlist2dawg ../word_lists/word_list.txt pkmngb_en.word-dawg pkmngb_en.unicharset
	wordlist2dawg ../word_lists/top_100_word_list.txt pkmngb_en.freq-dawg pkmngb_en.unicharset

	mv shapetable pkmngb_en.shapetable
	mv normproto pkmngb_en.normproto
	mv inttemp pkmngb_en.inttemp
	mv pffmtable pkmngb_en.pffmtable
	mv unicharset pkmngb_en.unicharset

	combine_tessdata pkmngb_en.

